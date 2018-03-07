# -*- coding: utf-8 -*-
"""
Parser for the KKR Code.
The parser should never fail, but it should catch 
all errors and warnings and show them to the user.
"""

from aiida.parsers.parser import Parser
from aiida.orm.data.parameter import ParameterData
from aiida_kkr.calculations.kkr import KkrCalculation
from aiida.common.exceptions import InputValidationError
from aiida_kkr.tools.kkrparser_functions import parse_kkr_outputfile, check_error_category


__copyright__ = (u"Copyright (c), 2017, Forschungszentrum Jülich GmbH, "
                 "IAS-1/PGI-1, Germany. All rights reserved.")
__license__ = "MIT license, see LICENSE.txt file"
__version__ = "0.3"
__contributors__ = ("Jens Broeder", "Philipp Rüßmann")


class KkrParser(Parser):
    """
    Parser class for parsing output of KKR code..
    """

    def __init__(self, calc):
        """
        Initialize the instance of KkrParser
        """
        # check for valid input
        if not isinstance(calc, KkrCalculation):
            raise InputValidationError("Input calc must be a KkrCalculation")
        
        self._ParserVersion = __version__

        #reuse init of base class
        super(KkrParser, self).__init__(calc)
        

    # pylint: disable=protected-access
    def parse_with_retrieved(self, retrieved):
        """
        Parse output data folder, store results in database.

        :param retrieved: a dictionary of retrieved nodes, where
          the key is the link name
        :returns: a tuple with two values ``(bool, node_list)``, 
          where:

          * ``bool``: variable to tell if the parsing succeeded
          * ``node_list``: list of new nodes to be stored in the db
            (as a list of tuples ``(link_name, node)``)
        """
        success = False
        node_list = ()

        # Check that the retrieved folder is there
        try:
            out_folder = retrieved[self._calc._get_linkname_retrieved()]
        except KeyError:
            self.logger.error("No retrieved folder found")
            return success, node_list

        # check what is inside the folder
        list_of_files = out_folder.get_folder_list()

        # we need at least the output file name as defined in calcs.py
        if self._calc._OUTPUT_FILE_NAME not in list_of_files:
            self.logger.error("Output file not found")
            return success, node_list

        # Parse output files of KKR calculation
        try:
            outfile = out_folder.get_abs_path(self._calc._OUTPUT_FILE_NAME)
        except OSError:
            self.logger.error
        
        # get path to files and catch errors if files are not present
        file_errors = []
        # append tupels (error_category, error_message) where error_category is 
        # 1: critical error, always leads to failing of calculation
        # 2: warning, is inspected and checked for consistency with read-in 
        #    out_dict values (e.g. nspin, newsosol, ...)
        try:
            fname = self._calc._OUTPUT_0_INIT
            outfile_0init = out_folder.get_abs_path(fname)  
        except OSError:
            file_errors.append((1, "Critical error! OUTPUT_0_INIT not found {}".format(fname)))
            outfile_0init = None
        try:
            fname = self._calc._OUTPUT_000
            outfile_000 = out_folder.get_abs_path(fname)
        except OSError:
            file_errors.append((1, "Critical error! OUTPUT_000 not found {}".format(fname)))
            outfile_000 = None
        try:
            fname = self._calc._OUTPUT_2
            outfile_2 = out_folder.get_abs_path(fname)
        except OSError:
            file_errors.append((1, "Critical error! OUTPUT_2 not found {}".format(fname)))
            outfile_2 = None
        try:
            fname = self._calc._OUT_POTENTIAL
            potfile_out = out_folder.get_abs_path(fname)
        except OSError:
            file_errors.append((1, "Critical error! OUT_POTENTIAL not found {}".format(fname)))
            potfile_out = None
        try:
            fname = self._calc._OUT_TIMING_000
            timing_file = out_folder.get_abs_path(fname)
        except OSError:
            file_errors.append((1, "Critical error! OUT_TIMING_000  not found {}".format(fname)))
            timing_file = None
        try:
            fname = self._calc._NONCO_ANGLES_OUT
            nonco_out_file = out_folder.get_abs_path(fname)
        except OSError:
            file_errors.append((2, "Error! NONCO_ANGELS_OUT not found {}".format(fname)))
            nonco_out_file = None
        #
        #potfile_in = out_folder.get_abs_path(self._calc._POTENTIAL)
        #scoef_file = out_folder.get_abs_path(self._calc._SCOEF)
        
        
        out_dict = {'parser_version': self._ParserVersion, 
                    'calculation_plugin_version': self._calc._CALCULATION_PLUGIN_VERSION}
        
        #TODO job title, compound description
        success, msg_list, out_dict = parse_kkr_outputfile(out_dict, outfile, 
                                                           outfile_0init, 
                                                           outfile_000, 
                                                           timing_file, 
                                                           potfile_out,
                                                           nonco_out_file,
                                                           outfile_2)
        out_dict['parser_errors'] = msg_list
         # add file open errors to parser output of error messages
        for (err_cat, f_err) in file_errors: 
            if err_cat == 1:
                msg_list.append(f_err)
            elif check_error_category(err_cat, f_err, out_dict):
                msg_list.append(f_err)
            else:
                if 'parser_warnings' not in out_dict.keys():
                    out_dict['parser_warnings'] = []
                out_dict['parser_warnings'].append(f_err.replace('Error', 'Warning'))
        out_dict['parser_errors'] = msg_list
        
        #create output node and link
        output_data = ParameterData(dict=out_dict)
        link_name = self.get_linkname_outparams()
        node_list = [(link_name, output_data)]
        
        return success, node_list
    
