"""
Copyright (C) 2015  Genome Research Ltd.

Author: Irina Colgiu <ic4@sanger.ac.uk>

This program is part of metadata-check

metadata-check is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.
You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

This file has been created on Feb 10, 2015.
"""

from irods import api as irods_api
from irods import icommands_wrapper
from header_parser import sam_header_analyser as header_analyser
import os
from identifiers import EntityIdentifier as Identif
from com import  utils as common_utils
import error_types


class GeneralUtils:

    @classmethod
    def check_same_entities(cls, seqsc_entities, entity_type):
        problems = []
        id_types = seqsc_entities.keys()
        for i in xrange(1, len(id_types)-1):
            if seqsc_entities.get(id_types[i-1]) and seqsc_entities.get(id_types[i]):
                if not set(seqsc_entities.get(id_types[i-1])) == set(seqsc_entities.get(id_types[i])):
                    problems.append(str(error_types.DifferentEntitiesFoundInSeqscapeQueryingByDiffIdTypesError(entity_type=entity_type,
                                                                                         id_type1=id_types[i-1],
                                                                                         id_type2=id_types[i],
                                                                                         entities_set1=seqsc_entities[id_types[i-1]],
                                                                                         entities_set2=seqsc_entities[id_types[i]])))
        return problems


class HeaderUtils:

    @classmethod
    def sort_entities_by_guessing_id_type(cls, ids_list):
        """
            This function takes a list of ids, which it doesn't know what type they are,
            guesses the id type and then returns a dict containing 3 lists - one for each type of id
            (internal_id, accession_number, name).
            Parameters
            ----------
                ids_list : list - containing together all sorts of ids that identify entities.
            Returns
            -------
                sorted_ids : dict - {'name': list, 'accession_number': list, 'internal_id': list}
        """
        sorted_ids = {'name': [], 'accession_number': [], 'internal_id': []}
        for entity_id in ids_list:
            id_type = Identif.guess_identifier_type(entity_id)
            sorted_ids[id_type].append(entity_id)
        return sorted_ids


    @classmethod
    def _get_parsed_header(cls, path, location):
        if location == 'irods':
            full_header = header_analyser.BAMHeaderAnalyser.extract_header_from_irods_file(path)
        elif location == 'lustre':
            full_header = header_analyser.BAMHeaderAnalyser.extract_header_from_file(path)
        else:
            raise ValueError("This function accepts as file location only irods or lustre.")
        parsed_header = header_analyser.BAMHeaderAnalyser.parse_header(full_header)
        header_metadata = header_analyser.BAMHeaderAnalyser.extract_metadata_from_header(parsed_header)
        return header_metadata

    @classmethod
    def get_parsed_header_from_irods_file(cls, irods_path):
        return cls._get_parsed_header(irods_path, 'irods')


    @classmethod
    def get_parsed_header_from_lustre_file(cls, lustre_path):
        return cls._get_parsed_header(lustre_path, 'lustre')



class iRODSUtils:

    # @classmethod
    # def retrieve_list_of_bams_by_study_from_irods(cls, study_name):
    #     avus = {'study': study_name, 'type': 'bam'}
    #     bams = icommands_wrapper.iRODSMetaQueryOperations.query_by_metadata(avus)
    #     filtered_files = icommands_wrapper.iRODSMetaQueryOperations.filter_out_bam_phix_files(bams)
    #     return filtered_files
    #
    # @classmethod
    # def retrieve_list_of_crams_by_study_from_irods(cls, study_name):
    #     avus = {'study': study_name, 'type': 'cram'}
    #     crams = icommands_wrapper.iRODSMetaQueryOperations.query_by_metadata(avus)
    #     filtered_files = icommands_wrapper.iRODSMetaQueryOperations.filter_out_cram_phix_files(crams)
    #     return filtered_files
    #
    # @classmethod
    # def retrieve_list_of_files_by_study_name(cls, study_name):
    #     avus = {'study' : study_name}
    #     files = icommands_wrapper.iRODSMetaQueryOperations.query_by_metadata(avus)
    #     filtered_files = icommands_wrapper.iRODSMetaQueryOperations.filter_out_phix(files)
    #     return filtered_files

    @classmethod
    def retrieve_list_of_target_qc_pass_files_by_metadata(cls, attribute, value):
        avus = {attribute : value, 'target' : '1', 'manual_qc' : '1'}
        files = icommands_wrapper.iRODSMetaQueryOperations.query_by_metadata(avus)
        #filtered_files = icommands_wrapper.iRODSMetaQueryOperations.filter_out_phix(files)
        return filtered_files

    @classmethod
    def retrieve_list_of_target_files_by_metadata(cls, attribute, value):
        avus = {attribute : value, 'target' : '1'}
        files = icommands_wrapper.iRODSMetaQueryOperations.query_by_metadata(avus)
        #filtered_files = icommands_wrapper.iRODSMetaQueryOperations.filter_out_phix(files)
        return filtered_files

    @classmethod
    def retrieve_list_of_files_by_avus(cls, avus_dict):
        #avus = {attribute : value, 'target' : '1', 'manual_qc' : '1'}
        files = icommands_wrapper.iRODSMetaQueryOperations.query_by_metadata(avus_dict)
        #filtered_files = icommands_wrapper.iRODSMetaQueryOperations.filter_out_phix(files)
        #return filtered_files
        return files

    @classmethod
    def retrieve_list_of_files_by_metadata(cls, attribute, value):
        avus = {attribute : value}
        files = icommands_wrapper.iRODSMetaQueryOperations.query_by_metadata(avus)
        #filtered_files = icommands_wrapper.iRODSMetaQueryOperations.filter_out_phix(files)
        #return filtered_files
        return files


    @classmethod
    def retrieve_irods_avus(cls, irods_path):
        return irods_api.iRODSAPI.retrieve_metadata_for_file(irods_path)

    @classmethod
    def extract_values_for_key_from_irods_metadata(cls, avus_list, key):
        results = []
        for avu in avus_list:
            if avu.attribute == key:
                results.append(avu.value)
        return results

    @classmethod
    def extract_lanelet_name(cls, irods_path):
        lanelet_file = os.path.basename(irods_path)
        return lanelet_file


    # TODO: test - what if the lanelet is a whole lane (x10 data)? TO add unittest for this!
    @classmethod
    def guess_seq_irods_path_from_lustre_path(cls, lustre_path):
        """
            Applies only for the data delivered by NPG.

        """
        fname = common_utils.extract_fname_from_path(lustre_path)
        run_id = fname.split("_")
        irods_fpath = "/seq/" + run_id[0] + "/" + fname
        return irods_fpath



    @classmethod
    def extract_samples_from_irods_metadata(cls, irods_metadata):
        irods_sample_names_list = cls.extract_values_for_key_from_irods_metadata(irods_metadata, 'sample')
        irods_sample_acc_nr_list = cls.extract_values_for_key_from_irods_metadata(irods_metadata, 'sample_accession_number')
        irods_sample_internal_id_list = cls.extract_values_for_key_from_irods_metadata(irods_metadata, 'sample_id')
        irods_samples = {'name': irods_sample_names_list,
                         'accession_number': irods_sample_acc_nr_list,
                         'internal_id': irods_sample_internal_id_list
        }
        return irods_samples

    @classmethod
    def extract_studies_from_irods_metadata(cls, irods_metadata):
        irods_study_names_list = cls.extract_values_for_key_from_irods_metadata(irods_metadata, 'study')
        irods_study_internal_id_list = cls.extract_values_for_key_from_irods_metadata(irods_metadata, 'study_id')
        irods_study_acc_nr_list = cls.extract_values_for_key_from_irods_metadata(irods_metadata, 'study_accession_number')
        irods_studies = {'name': irods_study_names_list,
                         'internal_id': irods_study_internal_id_list,
                         'accession_number': irods_study_acc_nr_list
        }
        return irods_studies


    @classmethod
    def extract_libraries_from_irods_metadata(cls, irods_metadata):
        irods_lib_internal_id_list = cls.extract_values_for_key_from_irods_metadata(irods_metadata, 'library_id')
        irods_lib_names_list = cls.extract_values_for_key_from_irods_metadata(irods_metadata, 'library')

        # HACKS for the inconsistencies in iRODS, in which NPG submits under library name the actual library id
        lib_ids = list(set(irods_lib_internal_id_list + irods_lib_names_list))
        ids_dict = {'name': [], 'accession_number': [], 'internal_id': []}
        for id in lib_ids:
            id_type = Identif.guess_identifier_type(id)
            ids_dict[id_type].append(id)
        return ids_dict

