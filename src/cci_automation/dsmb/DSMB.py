#!/usr/bin/env python3
from datetime import date
from typing import Optional

import pandas as pd

from clinical_reporting.data import read_data_dict_zip_corelisting


class DSMB:
    def __init__(
        self,
        study_name: str,
        input_dir: str,
        output_dir: str,
        output_file_name: str,
        cutoff_date: Optional[date] = None,
    ):
        """DSMB for any study

        Args:
            study_name (string): study selected for the DSMB
            input_dir (string): core listing folder folder/directory path
            output_dir (string): file path where the report is gonna be saved
            Optional cutoff_date (date): cutoff date for the report
        """
        if input_dir is None:
            print("No dir selected!")
        else:
            self.study_name = study_name
            self.output_dir = output_dir
            self.output_file_name = output_file_name
            self.input_data = read_data_dict_zip_corelisting(input_dir, cutoff_date)
            self.data_analysis(self.input_data, self.study_name)

    def data_analysis(self, data, study_name):
        """
        Perform data analysis based on the study name.

        This method analyzes the input data based on the study name provided. It sets the display options for pandas to show all columns and rows. Then, depending on the study name, it imports the corresponding DSMB module and calls its main function with the necessary parameters.

        Parameters:
        - self.input_data: The input data for analysis.
        - self.output_dir: The directory to save the output files.
        - self.output_file_name: The name of the output file.

        Returns:
        None
        """
        pd.set_option("display.max_columns", None)
        pd.set_option("display.max_rows", None)
        if study_name == "12423":
            from .DSMB12423 import DSMB12423

            x = DSMB12423(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()
        if study_name == "11823":
            from .DSMB11823 import DSMB11823

            x = DSMB11823(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()

        if study_name == "15122":
            from .DSMB15122 import DSMB15122

            DSMB15122(
                data,
                export=True,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
        if study_name == "03821":
            from .DSMB03821 import DSMB03821

            DSMB03821(
                data,
                export=True,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
                #   debug=self.debug,
            )

        if study_name == "15420":
            from .DSMB15420 import DSMB15420

            DSMB15420(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )

        if study_name == "16321":
            from .DSMB16321 import DSMB16321

            x = DSMB16321(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()

        if study_name == "03325":
            from .DSMB03325 import DSMB03325

            x = DSMB03325(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()

        if study_name == "10325":
            from .DSMB10325 import DSMB10325

            x = DSMB10325(
                data,
                output_dir=self.output_dir,
                output_file_name=self.output_file_name,
            )
            x.run()
