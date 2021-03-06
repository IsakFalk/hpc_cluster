import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import ParameterGrid

PRE_STRING = "#$ -l h_rt={h_rt}\n"
GPU_FLAG_STRING = "#$ -l gpu=true\n"
H_VMEM_FLAG_STRING = "#$ -l h_vmem={h_vmem}G\n"
EMAIL_FLAG_STRING = "#$ -m {email_flags}\n"
EMAIL_ADDRESS_STRING = "#$ -M {email_address}\n"

ARRAY_JOB_TEMPLATE = """
# This is an autogenerated template from the python library: cluster
# Please set the below flags if they have not been filled in
#$ -l tmem={tmem}G
#$ -l h_rt={h_rt}
#$ -j y
#$ -S /bin/bash
#$ -N {job_name}
#$ -t 1-{total_number_of_jobs}
#$ -wd {working_dir}

CURRENT_JOB_OUTPUT_DIR={job_output_dir}/{script_name}
RUN_OUTPUT_DIR=${{CURRENT_JOB_OUTPUT_DIR}}/n${{SGE_TASK_ID}}
mkdir -p ${{RUN_OUTPUT_DIR}}

# Please export necessary libraries
source {source_path}

hostname
date
{program} {script_path} --csv_path {csv_path} --extract_line ${{SGE_TASK_ID}} --output_dir ${{RUN_OUTPUT_DIR}}
date
"""


class ArrayJob:
    def __init__(
        self,
        param_dict,
        working_dir,
        source_path,
        script_path,
        job_submission_files_dir,
        job_output_dir,
        program,
        tmem,
        h_vmem,
        h_rt,
        gpu,
        sep="\t",
        email_flags="n",
        email_address=None,
    ):
        """
        :param param_dict: dictionary of parameters, where keys correspond to parameter name and values of objects
        to search over, with values as list
        :param working_dir: working directory to run job from
        :param script_path: path to script that will be run over combinations of parameters
        :param source_path: path to source file (to source software)
        :param job_submission_files_dir: path to directory where job submission file will be written to
        :param job_output_dir: path to directory where the job will write data to
        :param program: program to run on script
        :param tmem: scheduler FLAG, amount of memory to reserve
        :param h_vmem: scheduler FLAG, memory limit, jobs using more memory will be killed
        :param h_rt: scheduler FLAG, time to run (in seconds)
        :param gpu: scheduler FLAG, reserve GPU for job
        :param email_flags: FLAGs for when to send email, list of option: http://gridscheduler.sourceforge.net/htmlman/htmlman1/qsub.html
        :param email_address: email address to send the emails generated from email_flags
        :param sep: separator for CSV files holding parameters (default TSV)
        """
        self.param_dict = param_dict
        self.param_flattened_df = _from_dict_to_long_df_format(self.param_dict)
        self.working_dir = Path(working_dir)
        self.source_path = Path(source_path)

        self.script_path = Path(script_path).resolve()
        self.script_name = self.script_path.stem
        self.script_dir = self.script_path.parent

        self.job_submission_files_dir = Path(job_submission_files_dir).resolve()
        self.job_output_dir = Path(job_output_dir).resolve()
        self.current_job_dir = self.job_output_dir / self.script_name
        self.current_job_dir.resolve().mkdir(parents=True, exist_ok=True)
        self.csv_path = self.current_job_dir / "parameters_flat.csv"

        self.program = program
        self.tmem = tmem
        self.h_vmem = h_vmem
        self.h_rt = h_rt
        self.gpu = gpu
        self.email_flags = email_flags
        self.email_address = email_address

        self.sep = sep

        # This order is mandatory
        self._save_parameters_to_csv()
        self._dump_metadata_to_current_job_dir()
        self._create_job_template()
        self._write_job_submission_file()

    def _create_job_template(self):
        nrows, _ = self.param_flattened_df.shape
        # -t gpu=false does not exist, absence of flag means don't use gpu
        # if we use gpu, we need to remove h_vmem flag
        # TODO: Should probably do this in a smarter way
        if self.gpu:
            self.job_template = ARRAY_JOB_TEMPLATE.replace(
                PRE_STRING, PRE_STRING + GPU_FLAG_STRING
            )
            self.filled_in_job_template = self.job_template.format(
                tmem=self.tmem,
                h_rt=self.h_rt,
                job_name=str(self.script_name),
                total_number_of_jobs=nrows,
                working_dir=str(self.working_dir),
                script_name=str(self.script_name),
                job_output_dir=str(self.job_output_dir),
                source_path=str(self.source_path),
                program=self.program,
                script_path=str(self.script_path),
                csv_path=str(self.csv_path),
            )
        else:
            self.job_template = ARRAY_JOB_TEMPLATE.replace(
                PRE_STRING, PRE_STRING + H_VMEM_FLAG_STRING
            )
            self.filled_in_job_template = self.job_template.format(
                tmem=self.tmem,
                h_rt=self.h_rt,
                h_vmem=self.h_vmem,
                job_name=str(self.script_name),
                total_number_of_jobs=nrows,
                working_dir=str(self.working_dir),
                script_name=str(self.script_name),
                job_output_dir=str(self.job_output_dir),
                source_path=str(self.source_path),
                program=self.program,
                script_path=str(self.script_path),
                csv_path=str(self.csv_path),
            )

    def _write_job_submission_file(self):
        with open(self.job_submission_files_dir / (self.script_name + ".sh"), "w") as f:
            f.write(self.filled_in_job_template)

    def _dump_metadata_to_current_job_dir(self):
        with open(self.current_job_dir / "parameters.json", "w") as f:
            json.dump(self.param_dict, f, indent=4)

    def _save_parameters_to_csv(self):
        self.param_flattened_df.to_csv(
            path_or_buf=self.csv_path, sep=self.sep,
        )


def _from_dict_to_long_df_format(param_dict):
    """Take a dictionary and unpack this into tabular dataframe

    :param_dict: (dict) dictionary of key and the values of the key
    that we want to perform grid search over
    :return df: (pd.DataFrame) dataframe of the grid in flattened form"""
    # sklean ParamterGrid needs to be massaged into a dictionary
    # of the form {'param_i': [${flattened values}]}
    df_dict = {}
    for key in param_dict.keys():
        df_dict[key] = []

    param_grid = ParameterGrid(param_dict)
    for row in param_grid:
        for key, val in row.items():
            df_dict[key].append(val)
    return pd.DataFrame.from_dict(df_dict)


def save_csv_grid(param_grid, path, sep="\t"):
    _from_dict_to_long_df_format(param_grid).to_csv(
        path_or_buf=path, sep=sep,
    )


def extract_csv_to_dict(path, extract_line, sep="\t"):
    assert extract_line > 0
    df = pd.read_csv(path, sep=sep, index_col=0)
    dd = df.to_dict("records")[extract_line - 1]
    return dd
