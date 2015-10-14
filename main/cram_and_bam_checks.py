#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

"""
Created on Dec 02, 2014

Author: Irina Colgiu <ic4@sanger.ac.uk>

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation; either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
 
"""

import os
import arg_parser
import metadata_utils
#from main import irods_seq_data_tests as seq_tests
import irods_metadata_consistency_checks as seq_consistency_checks
import error_types
import complete_irods_metadata_checks
import irods_metadata_consistency_checks as irods_checks
import irods_metadata as irods_meta_module
import header_metadata as header_meta_module
#from ... import config
import config
import constants
from collections import defaultdict
from identifiers import EntityIdentifier, IdentifierMapper
from irods_baton import baton_wrapper as baton
import sys
import os
from com import utils
from irods import icommands_wrapper
from seqscape.queries import query_study

#BOTH_FILE_TYPES = 'both'


def check_irods_vs_header_metadata(irods_path, header_dict, irods_dict, entity_type):
    """
        where: (e.g.)
         irods_dict = dict('name': [sample_name], accession_number: [samples_acc_nr], internal_id: [internal_id])
         header_dict = dict('name': [sample_name], accession_number: [samples_acc_nr], internal_id: [internal_id])
    """
    problems = []
    for id_type, head_ids_list in header_dict.iteritems():
        if irods_dict.get(id_type) and header_dict.get(id_type):
            if set(head_ids_list).difference(set(irods_dict[id_type])):
                problems.append(error_types.HeaderVsIrodsMetadataAttributeError(fpath=irods_path, attribute=id_type,
                                                                      header_value=str(head_ids_list),
                                                                      irods_value=irods_dict[id_type],
                                                                      entity_type=entity_type))
    return problems



def read_file_into_list(fofn_path):
    fofn_fd = open(fofn_path)
    files_list = [f.strip() for f in fofn_fd]
    fofn_fd.close()
    return files_list


def write_list_to_file(input_list, output_file, header=None):
    out_fd = open(output_file, 'a')
    if header:
        out_fd.write(header+'\n')
    for entry in input_list:
        out_fd.write(entry+'\n')
    out_fd.write('\n')
    out_fd.close()

def write_tuples_to_file(tuples, output_file, header_tuple=None):
    out_fd = open(output_file, 'a')
    for elem in header_tuple:
        out_fd.write(str(elem)+"\t")
    out_fd.write("\n")
    for tup in tuples:
        for elem in tup:
            out_fd.write(str(elem)+"\t")
        out_fd.write("\n")
    out_fd.close()



def collect_fpaths_by_study_name(study_name):
    avus_dict = {'study': study_name}
    return metadata_utils.iRODSiCmdsUtils.retrieve_list_of_files_by_avus(avus_dict)

def collect_fpaths_by_study_name_and_filter(study_name, filter_dict):
    avus_dict = {'study': study_name}
    avus_dict.update(filter_dict)
    return metadata_utils.iRODSiCmdsUtils.retrieve_list_of_files_by_avus(avus_dict)

def collect_fpaths_by_study_accession_nr_and_filter(study_acc_nr, filter_dict):
    avus_dict = {'study_accession_number': study_acc_nr}
    avus_dict.update(filter_dict)
    return metadata_utils.iRODSiCmdsUtils.retrieve_list_of_files_by_avus(avus_dict)

def collect_fpaths_by_study_internal_id_and_filter(study_id, filter_dict):
    avus_dict = {'study_id': study_id}
    avus_dict.update(filter_dict)
    return metadata_utils.iRODSiCmdsUtils.retrieve_list_of_files_by_avus(avus_dict)

# def collect_fpaths_by_study_identif_and_filter(id_type, id_value, filter_dict):
#     return metadata_utils.iRODSUtils.retrieve_list_of_files_by_avus({id_type: id_value}.update(filter_dict))

def check_same_files_by_diff_study_ids(name, internal_id, acc_nr, filters_dict):  # filters can be: None => get any value for this tag, 1, or 0
    files_by_name = set(collect_fpaths_by_study_name_and_filter(str(name), filters_dict))
    files_by_acc_nr = set(collect_fpaths_by_study_accession_nr_and_filter(str(acc_nr), filters_dict))
    files_by_id = set(collect_fpaths_by_study_internal_id_and_filter(str(internal_id), filters_dict))

    problems = []
    if files_by_name != files_by_acc_nr:
        diffs = files_by_name.difference(files_by_acc_nr)
        if diffs:
            problems.append(error_types.DifferentFilesRetrievedByDiffStudyIdsOfSameStudy(diffs, 'name', 'accession_number'))

        diffs = files_by_acc_nr.difference(files_by_name)
        if diffs:
            problems.append(error_types.DifferentFilesRetrievedByDiffStudyIdsOfSameStudy(diffs, 'accession_number', 'name'))

    if files_by_name != files_by_id:
        diffs = files_by_name.difference(files_by_id)
        if diffs:
            problems.append(error_types.DifferentFilesRetrievedByDiffStudyIdsOfSameStudy(diffs, 'name', 'internal_id'))

        diffs = files_by_id.difference(files_by_name)
        if diffs:
            problems.append(error_types.DifferentFilesRetrievedByDiffStudyIdsOfSameStudy(diffs, 'internal_id', 'name'))

    if files_by_acc_nr != files_by_id:
        diffs = files_by_id.difference(files_by_acc_nr)
        if diffs:
            problems.append(error_types.DifferentFilesRetrievedByDiffStudyIdsOfSameStudy(diffs, 'internal_id', 'accession_number'))

        diffs = files_by_acc_nr.difference(files_by_id)
        if diffs:
            problems.append(error_types.DifferentFilesRetrievedByDiffStudyIdsOfSameStudy(diffs, 'accession_number', 'internal_id'))
    return problems


def collect_fpaths_from_args(study=None, file_type=constants.CRAM_FILE_TYPE, files_list=None, fofn_path=None):
    if study:
        fpaths_irods = collect_fpaths_by_study_name(study, file_type)
    elif fofn_path:
        fpaths_irods = read_file_into_list(fofn_path)
    elif files_list:
        fpaths_irods = files_list
    return fpaths_irods

def collect_fpaths_for_samples(samples):
    pass

def filter_by_file_type(fpaths, file_type):
    return [f for f in fpaths if f.endswith(file_type)]

def infer_file_type(fpath):
    if fpath.endswith(constants.BAM_FILE_TYPE):
        return constants.BAM_FILE_TYPE
    elif fpath.endswith(constants.CRAM_FILE_TYPE):
        return constants.CRAM_FILE_TYPE
    else:
        raise NotImplementedError("Infer file type was not implemented for " + str(fpath))



def filter_by_avu(fpath, avu_attribute, avu_value):
    pass# manual_qc,...

def decide_which_tests(all_tests=None, test_sample=None, test_library=None, test_study=None, desired_reference=None, test_md5=None, test_filename=None, test_complete_meta=None):
    run_header_tests = False
    run_irods_tests = False
    if all_tests:
        run_header_tests = True
        run_irods_tests = True
    else:
        if test_sample:
            if 'all' in test_sample or 'irods_vs_header' in test_sample:
                run_header_tests = True
        if test_library:
            if 'irods_vs_header' in test_library or 'all' in test_library:
                run_header_tests = True
        if any([test_sample, test_library, test_study, desired_reference, test_md5, test_filename, all_tests, test_complete_meta]):
            run_irods_tests = True
    return {'header_tests' : run_header_tests, 'irods_tests' : run_irods_tests}


#def process_with_baton():
def main():
    args = arg_parser.parse_args()

    # Decide on which categories of tests to run:
    # tests_dict = decide_which_tests(args.all_tests, args.test_sample, args.test_library, args.test_study,
    #                                 args.desired_reference, args.test_md5, args.test_filename, args.test_complete_meta)
    # run_irods_tests = tests_dict['irods_tests']
    # run_header_tests = tests_dict['header_tests']

    # h_meta = None
    # i_meta = None

    header_meta_needed = is_header_metadata_needed(args)
    irods_meta_needed = is_irods_metadata_needed(args)

    all_h_samples = set()
    all_h_libraries = set()
    all_i_samples_by_names = set()
    all_i_samples_by_egaids = set()

    all_i_libraries_by_ids = set()
    all_i_libraries_by_names = set()

    all_i_studies_by_egaids = set()
    all_i_studies_by_names = set()

    # TODO: implement here also the option of getting a list of files as input
    # in which case use:metadata_utils.BatonStuff.from_metalist_results_to_avus




    # for f in filtered_fpaths:
    #     problems = []
    #     if args.config_file:
    #         pass
    #
    #     # Retrieve the resources as needed in preparation for the tests:
    #     h_meta = None
    #     if header_meta_needed:
    #         try:
    #             header = metadata_utils.HeaderUtils.get_parsed_header_from_irods_file(f)
    #         except IOError as e:
    #             problems.append(str(e))
    #             continue
    #         else:
    #             h_meta = header_meta_module.HeaderSAMFileMetadata.from_header_to_metadata(header, f)
    #             sanity_issues = h_meta.run_field_sanity_checks_and_filter()
    #             problems.extend(sanity_issues)
    #
    #             # populate the samples and libraries for outputting them (in case someone asked for them)
    #             all_h_samples.update(header.rg.samples)
    #             all_h_libraries.update(header.rg.libraries)


    all_problems = []
    issues_per_file = {}
    # GET THE FILES AND METADATA:
    if irods_meta_needed:

        # QUERY BY AVUS and get AVUS for all the data objects found:
        #search_criteria = put_together_search_criteria(some_args)
        filters = {}
        search_criteria = []
        if args.study_name:
            search_criteria.append(('study', args.study_name))
        elif args.study_acc_nr:
            search_criteria.append(('study_accession_number', args.study_acc_nr))
        elif args.study_internal_id:
            search_criteria.append(('study_id', args.study_internal_id))

        if search_criteria:
            if args.filter_npg_qc:
                search_criteria.append(('manual_qc', args.filter_npg_qc))
                filters['manual_qc'] = args.filter_npg_qc
            if args.filter_target:
                search_criteria.append(('target', args.filter_target))
                filters['target'] = args.filter_target

            print "SEARCH CRITERIA : " + str(search_criteria)
            # run baton to get the list of files by the search criteria...hmm, or add the sample filter on the top of the study filter?!
            try:
                metaquery_results = baton.BatonAPI.query_by_metadata_and_get_results_as_json(search_criteria) # avu_tuple_list
            except IOError as e:
                all_problems.append(e)

            fpaths_checksum_and_avus = metadata_utils.iRODSBatonUtils.from_metaquery_results_to_fpaths_and_avus(metaquery_results)  # this is a dict of key = fpath, value = dict({'avus':[], 'checksum':str})

            print "NR OF FPATHS FOUND: " + str(len(fpaths_checksum_and_avus))

        # if args.samples:
        #     samples = args.samples
        #     if args.fosn:
        #         samples = read_file_into_list(args.fosn)
        #
        #     metaquery_results = []
        #     if samples:
        #         for sampl in args.samples:
        #             std_id_type = EntityIdentifier.guess_identifier_type(sampl)
        #             irods_id_type = IdentifierMapper.seqsc2irods(std_id_type, 'sample')
        #             search_criteria_for_sample = search_criteria + [(irods_id_type, sampl)]
        #
        #             # WARNING! this might run the machine out of memory cause I am reading into memory all the metadata => if the search returns all the files in iRODS ever submitted...I'm done!
        #             f_and_meta_irods = baton.BatonAPI.query_by_metadata_and_get_results_as_json(search_criteria_for_sample)
        #             metaquery_results.append(f_and_meta_irods)

        #print "FPATHS and avus: " + str(metaquery_results)

         ########################## TESTS #####################
        # PREPARING FOR THE TESTS
        diff_files_problems = []
        study_obj = None
        if args.study_internal_id:
            study_obj = query_study(internal_id=args.study_internal_id)
        if args.study_name:
            study_obj = query_study(name=args.study_name)
        if args.study_acc_nr:
            study_obj = query_study(accession_number=args.study_acc_nr)
        if study_obj:
            issues = check_same_files_by_diff_study_ids(study_obj.name, study_obj.internal_id, study_obj.accession_number, filters)
            diff_files_problems.extend(issues)
        print "Ran check on the list of files retrieved by each study identifier -- result is: " + str(diff_files_problems)


        for fpath, meta_dict in fpaths_checksum_and_avus.items():
            problems = []
            avu_issues = irods_meta_module.IrodsSeqFileMetadata.run_avu_count_checks(fpath, meta_dict['avus'])
            problems.extend(avu_issues)

            i_meta = irods_meta_module.IrodsSeqFileMetadata.from_avus_to_irods_metadata(meta_dict['avus'], fpath)
            i_meta.ichksum_md5 = meta_dict['checksum']

            # Check for sanity before starting the tests:
            sanity_issues = i_meta.run_field_sanity_checks_and_filter()
            problems.extend(sanity_issues)


            # LATER ON this part!!!
            # need to get the files here....to have them here already
            if header_meta_needed:
                try:
                    header = metadata_utils.HeaderUtils.get_parsed_header_from_irods_file(fpath)
                except IOError as e:
                    problems.append(str(e))
                else:
                    h_meta = header_meta_module.HeaderSAMFileMetadata.from_header_to_metadata(header, fpath)

            # populate the samples and libraries for outputting them (in case someone asked for them)
            all_i_samples_by_names.update(i_meta.samples.get('name'))
            all_i_samples_by_egaids.update(i_meta.samples.get('accession_number'))

            all_i_libraries_by_names.update(i_meta.libraries.get('name'))
            all_i_libraries_by_ids.update(i_meta.libraries.get('internal_id'))

            all_i_studies_by_names.update(i_meta.studies.get('name'))
            all_i_studies_by_egaids.update(i_meta.studies.get('accession_number'))


            ## Filter by manual_qc:
            if not args.filter_npg_qc is None:
                if args.filter_npg_qc != i_meta.npg_qc:
                    continue


            ####### RUN THE TESTS: #########
            # MD5 tests:
            if args.test_md5 or args.all_tests:
                try:
                    i_meta.test_md5_calculated_vs_metadata()
                except (error_types.WrongMD5Error, error_types.TestImpossibleToRunError) as e:
                    problems.append(str(e))

            # TODO - not working properly
            #if args.test_reference or args.all_tests:
            if args.desired_reference or args.all_tests:
                try:
                    i_meta.test_reference(args.desired_reference)
                except (error_types.WrongReferenceError, error_types.TestImpossibleToRunError) as e:
                    problems.append(str(e))

            if args.test_filename or args.all_tests:
                try:
                    i_meta.test_lane_from_fname_vs_metadata()
                except (error_types.IrodsMetadataAttributeVsFileNameError, error_types.TestImpossibleToRunError) as e:
                    problems.append(str(e))

                try:
                    i_meta.test_run_id_from_fname_vs_metadata()
                except (error_types.IrodsMetadataAttributeVsFileNameError, error_types.TestImpossibleToRunError) as e:
                    problems.append(str(e))

                # TODO : test also the tag

            if args.test_sample or args.all_tests:
                if 'all' in args.test_sample or args.all_tests:
                    issues = check_irods_vs_header_metadata(fpath, h_meta.samples, i_meta.samples, 'sample')
                    problems.extend(issues)

                    issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.samples, 'sample')    #def compare_entity_sets_in_seqsc(entities_dict, entity_type):
                    problems.extend(issues)

                    issues = seq_consistency_checks.check_sample_is_in_desired_study(i_meta.samples['internal_id'], i_meta.studies['name'])
                    problems.extend(issues)
                else:
                    if 'irods_vs_header' in args.test_sample:
                        issues = check_irods_vs_header_metadata(fpath, h_meta.samples, i_meta.samples, 'sample')
                        problems.extend(issues)

                    if 'irods_vs_seqsc' in args.test_sample:
                        issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.samples, 'sample')    #def compare_entity_sets_in_seqsc(entities_dict, entity_type):
                        problems.extend(issues)

                        issues = seq_consistency_checks.check_sample_is_in_desired_study(i_meta.samples['internal_id'], i_meta.studies['name'])
                        problems.extend(issues)

            if args.test_library or args.all_tests:
                if args.all_tests or 'all' in args.test_library:
                    issues = check_irods_vs_header_metadata(fpath, h_meta.libraries, i_meta.libraries, 'library')
                    problems.extend(issues)

                    issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.libraries, 'library')
                    problems.extend(issues)
                else:
                    if 'irods_vs_header' in args.test_library:
                        issues = check_irods_vs_header_metadata(fpath, h_meta.libraries, i_meta.libraries, 'library')
                        problems.extend(issues)

                    if 'irods_vs_seqsc' in args.test_library:
                        issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.libraries, 'library')
                        problems.extend(issues)


            if args.test_study or args.all_tests:
                issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.studies, 'study')
                problems.extend(issues)


            if args.all_tests or args.test_complete_meta:
                # TODO: Add a warning that by default there is a default config file used
                if not args.config_file:
                    config_file = config.IRODS_ATTRIBUTE_FREQUENCY_CONFIG_FILE
                else:
                    config_file = args.config_file
                try:
                    diffs = complete_irods_metadata_checks.check_avus_freq_vs_config_freq(meta_dict['avus'], config_file)
                except IOError:
                    problems.append(error_types.TestImpossibleToRunError(fpath, "Test iRODS metadata is complete",
                                                                         "Config file missing: "+str(config_file)))
                else:
                    diffs_as_exc = complete_irods_metadata_checks.from_tuples_to_exceptions(diffs)
                    for d in diffs_as_exc:
                        d.fpath = fpath
                    problems.extend(diffs_as_exc)

            print "FILE: " + str(fpath) + " -- PROBLEMS found: " + str(problems)
            if problems:
                issues_per_file[fpath] = problems

            all_problems.extend(problems)

        print "NUMBER OF FILES WITH ISSUES: " + str(len(issues_per_file))
        print "NUMBER OF SAMPLES (by name) - IRODS FOUND: " + str(len(all_i_samples_by_names))
        print "NUMBER OF SAMPLES (by acc_nr) - IRODS FOUND: " + str(len(all_i_samples_by_egaids))
        print "NUMBER OF SAMPLES (by name) - HEADER FOUND: " + str(len(all_h_samples))

        # PRINT OUTPUT:
        # FILES EXCLUDED:
        # TODO: add an option in which you see also the files that were filtered out
        #print "FILES FILTERED OUT: "
        # for reason,files in files_excluded.iteritems():
        #     print "REASON: " + str(reason)
        #     for f_excl in files:
        #         str(f_excl)

        print "DIFFERENT FILES RETRIEVED BY QUERYING BY DIFF STUDY IDS: "
        for err in all_problems:
            if type(err) is error_types.DifferentFilesRetrievedByDiffStudyIdsOfSameStudy:
                print "Number of files retrieved when querying by: " + err.id1 + " and " + err.id2 + " = " + str(len(err.diffs))


        # # OUTPUTS
        if args.fofn_probl:
            write_list_to_file(issues_per_file.keys(), args.fofn_probl)


        ######## OUTPUT ENTITIES #######################
        study_name_as_ascii = args.study
        if args.study:
            study_name_as_ascii = ''.join([i if (ord(i) < 128 and ord(i) >= 65) or i == '_' else '' for i in args.study])

        out_dir = ''
        if args.entities_out_dir:
            out_dir = args.entities_out_dir
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)


        HEADER_SAMPLE_IDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.header.sample.ids')
        HEADER_LIBRARY_IDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.header.library.ids')
        IRODS_SAMPLE_NAMES_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.sample.names')
        IRODS_SAMPLE_EGAIDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.sample.egaids')
        IRODS_LIBRARY_NAMES_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.library.names')
        IRODS_LIBRARY_IDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.library.ids')
        IRODS_STUDY_NAMES_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.study.names')
        IRODS_STUDY_EGAIDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.study.egaids')

        ALL_ENTITIES_FILE = os.path.join(out_dir, study_name_as_ascii + '.entities.txt')

        FILE_OF_FNAMES_BY_FTYPES = os.path.join(study_name_as_ascii + '.fnames_by_ftypes.txt')

        ############ OUTPUT HEADER METADATA ############
        # outputting HEADER samples:
        if args.header_sample_ids_file:
            #write_list_to_file(all_h_samples, args.header_sample_ids_file)
            write_list_to_file(all_h_samples, HEADER_SAMPLE_IDS_FILE)

        # outputting HEADER libraries:
        if args.header_library_ids_file:
            #write_list_to_file(all_h_libraries, args.header_library_ids_file)
            write_list_to_file(all_h_libraries, HEADER_LIBRARY_IDS_FILE)

        ############ OUTPUT IRODS METADATA ###############
        # outputting IRODS samples by EGA ID:
        if args.sample_ega_out_file:
    #        write_list_to_file(all_i_samples_by_egaids, args.sample_ega_out_file)
            write_list_to_file(all_i_samples_by_egaids, IRODS_SAMPLE_EGAIDS_FILE)


        # outputting iRODS samples by name
        if args.sample_names_out_file:
    #        write_list_to_file(all_i_samples_by_names,args.sample_names_out_file)
            write_list_to_file(all_i_samples_by_names, IRODS_SAMPLE_NAMES_FILE)

        # outputting iRODS libraries by id
        if args.library_ids_out_file:
    #        write_list_to_file(all_i_libraries_by_ids, args.library_ids_out_file)
            write_list_to_file(all_i_libraries_by_ids, IRODS_LIBRARY_IDS_FILE)

        #outputting iRODS libraries by name
        if args.library_names_out_file:
    #        write_list_to_file(all_i_libraries_by_names,args.library_names_out_file)
            write_list_to_file(all_i_libraries_by_names, IRODS_LIBRARY_NAMES_FILE)

        ##### STUDIES #####
        # outputting IRODS studies by ega id:
        if args.study_egaids_out_file:
    #        write_list_to_file(all_i_studies_by_egaids, args.study_egaids_out_file)
            write_list_to_file(all_i_studies_by_egaids, IRODS_STUDY_EGAIDS_FILE)

        # outputting IRODS studies by name:
        if args.study_names_out_file:
    #        write_list_to_file(all_i_studies_by_names, args.study_names_out_file)
            write_list_to_file(all_i_studies_by_names, IRODS_STUDY_NAMES_FILE)


        ##################  OUTPUTTING ALL THE ENTITIES ########################
        if args.entities_out_file:
            write_list_to_file(all_h_samples, ALL_ENTITIES_FILE, header="HEADER SAMPLES")
            write_list_to_file(all_h_libraries, ALL_ENTITIES_FILE, header="HEADER LIBRARIES")
            write_list_to_file(all_i_samples_by_egaids, ALL_ENTITIES_FILE, header="IRODS SAMPLES BY EGA ID")
            write_list_to_file(all_i_samples_by_names, ALL_ENTITIES_FILE, header="IRODS SAMPLES BY NAME")
            write_list_to_file(all_i_libraries_by_ids, ALL_ENTITIES_FILE, header="IRODS LIBRARIES BY ID")
            write_list_to_file(all_i_libraries_by_names, ALL_ENTITIES_FILE, header="IRODS LIBRARIES BY NAME")
            write_list_to_file(all_i_studies_by_egaids, ALL_ENTITIES_FILE, header="IRODS STUDIES BY EGA ID")
            write_list_to_file(all_i_studies_by_names, ALL_ENTITIES_FILE, header="IRODS STUDIES BY NAME")


        #### OUTPUTTING the files by type ############
        # Count nr of files per type and build the sorted dict:
        counter_by_ftype = defaultdict(int)
        files_sorted_by_type = defaultdict(dict)  # dict of key = file name (no ext), value = dict - of type : fpath
        #for f in filtered_fpaths:
        for fpath in fpaths_checksum_and_avus:
            fname = utils.extract_fname_without_ext(fpath)
            ftype = infer_file_type(fpath)
            files_sorted_by_type[fname][ftype] = fpath
            counter_by_ftype[ftype] += 1

        # printing out the count of files per format:
        for format, n in counter_by_ftype.items():
            print "format = " + str(format) + " nr files = " + str(n)


        if args.fnames_by_ftype:
            # Going through the sorted files by type and put them in tuples
            ftypes_tuples = []
            wanted_ftypes = args.file_types
            for fname, ftypes_dict in files_sorted_by_type.items():
                ftyptes_per_fname = []
                for wanted_ft in wanted_ftypes:
                    fpath_per_type = ftypes_dict.get(wanted_ft) or 'missing'
                    ftyptes_per_fname.append(fpath_per_type)
                ftypes_tuples.append(ftyptes_per_fname)
            write_tuples_to_file(ftypes_tuples, FILE_OF_FNAMES_BY_FTYPES, wanted_ftypes)


            # Analyze the sorted dict to test that it all looks fine:
            missing_ftypes_errors = []
            for fname, files in files_sorted_by_type.items():
                existing_ftypes = set()
                wanted_ftypes = set(args.file_types)
                for f in files:
                    ftype = infer_file_type(f)
                    existing_ftypes.add(ftype)

                # CHeck if the existing file types are the wanted ones...
                if wanted_ftypes != existing_ftypes:
                    missing_ftypes = wanted_ftypes.difference(existing_ftypes)
                    missing_ftypes_errors.append(error_types.MissingFileFormatsFromIRODSError(fname, missing_ftypes))

            for error in missing_ftypes_errors:
                print str(error)






            # separate files from files_and_metadata_irods by file, and build a list of irodsMetadata objects ...

        #     if irods_meta_needed:
        #         irods_avus = metadata_utils.iRODSiCmdsUtils.retrieve_irods_avus(f)
        #         avu_issues = irods_meta_module.IrodsSeqFileMetadata.run_avu_count_checks(f, irods_avus)
        #         problems.extend(avu_issues)
        #
        #         i_meta = irods_meta_module.IrodsSeqFileMetadata.from_avus_to_irods_metadata(irods_avus, f)



            # TODO:  Remove duplicates for files..


            # irods_data = get_metadata_for_all_files(search_criteria)
            # metadata_per_file = get_meta_for_each_file(irods_data)  #split_meta_per_file# outputs a list of irods_metadata objects, one for each file
            # apply_filters(metadata_per_file)
            # for f in metadata_per_file:
            #     run tests
            #     add_issues_for_file_to_all_issues_container
            #
            #
            # # GET the AVUs for all the data objects found:
            # fpaths = []
            # if args.fofn:
            #     files_from_fofn = read_file_into_list(args.fofn)
            #     fpaths = files_from_fofn
            #
            # if args.files:
            #     fpaths = args.files
            #
            # for f in fpaths:
            #     metadata_per_file = get_irods_metadata_with_baton(f)
            #     apply_filters(metadata_per_file) # still the case?
            #
            #
            #
            # irods_avus = metadata_utils.iRODSUtils.retrieve_irods_avus(f)
            # avu_issues = irods_meta_module.IrodsSeqFileMetadata.run_avu_count_checks(f, irods_avus)
            # problems.extend(avu_issues)
            #
            # i_meta = irods_meta_module.IrodsSeqFileMetadata.from_avus_to_irods_metadata(irods_avus, f)
            #




def is_header_metadata_needed(args):
    # Deciding what tests to run
    header_meta_needed = False
    if args.all_tests:
        header_meta_needed = True
    else:
        if args.test_sample:
            if 'all' in args.test_sample or 'irods_vs_header' in args.test_sample:
                header_meta_needed = True
        if args.test_library:
            if 'irods_vs_header' in args.test_library or 'all' in args.test_library:
                header_meta_needed = True
        # check by wanted output:
        if any([args.header_sample_ids_file, args.header_library_ids_file]):
            header_meta_needed = True
    return header_meta_needed


def is_irods_metadata_needed(args):
    irods_meta_needed = False
    if args.all_tests:
        irods_meta_needed = True
    else:
        if any([args.test_sample, args.test_library, args.test_study, args.desired_reference, args.test_md5, args.test_filename, args.all_tests, args.config_file]):
            irods_meta_needed = True
        # check by wanted output:
        if any([args.sample_ega_out_file, args.sample_names_out_file, args.bad_sample_egaids_out_file,
                args.bad_sample_names_out_file, args.library_names_out_file, args.library_ids_out_file,
                args.bad_library_names_out_file, args.bad_library_ids_out_file, args.study_names_out_file,
                args.study_egaids_out_file, args.entities_out_dir, args.entities_out_file]):
            irods_meta_needed = True
    return irods_meta_needed


def main_imeta():
    args = arg_parser.parse_args()

    filters = {}
    if args.filter_target is not None:
        filters['target'] = args.filter_target
    if args.filter_npg_qc is not None:
        filters['manual_qc'] = args.filter_npg_qc


    # COLLECT FILE PATHS:
    fpaths_per_type = {} # type : [ fpath ]
    if args.study:
    #     if BAM_FILE_TYPE in args.file_types:
    #         fpaths_per_type[BAM_FILE_TYPE] = metadata_utils.iRODSUtils.retrieve_list_of_bams_by_study_from_irods(args.study)
    #     if CRAM_FILE_TYPE in args.file_types:
    #         fpaths_per_type[CRAM_FILE_TYPE] = metadata_utils.iRODSUtils.retrieve_list_of_crams_by_study_from_irods(args.study)
    # fpaths = fpaths_per_type.get(BAM_FILE_TYPE) + fpaths_per_type.get(CRAM_FILE_TYPE)

        #fpaths = metadata_utils.retrieve_list_of_files_by_study(args.study)
        fpaths = collect_fpaths_by_study_name_and_filter(args.study, filters)



    if args.fofn:
        files_from_fofn = read_file_into_list(args.fofn)
        fpaths = files_from_fofn

    if args.files:
        fpaths = args.files

    # per samples:
    if args.fosn:
        samples = read_file_into_list(args.fosn)
        # query irods for samples, get a list of files

    if args.samples:
        samples = args.samples
        # query irods per sample for files
        pass

    # Check for conflicts in the params?
    # TODO

    ##################### FILTER FILES ################################
    files_excluded = defaultdict(list) # key = reason, value = list of file paths

    ## Filter by file type ###
    filtered_fpaths = []
    for file_type in args.file_types:
        filtered_fpaths.extend(filter_by_file_type(fpaths, file_type))
    files_excluded['BY_FILE_TYPE'] = set(fpaths).difference(set(filtered_fpaths))

    if not filtered_fpaths:
        filtered_fpaths = fpaths
    print "ARGS = " + str(args)


    ########################## TESTS #####################
    # PREPARING FOR THE TESTS
    diff_files_problems = []
    if args.study_internal_id:
        study_obj = query_study(internal_id=args.study_internal_id)
    if args.study_name:
        study_obj = query_study(name=args.study_name)
    if args.study_acc_nr:
        study_obj = query_study(accession_number=args.study_acc_nr)
    if study_obj:
        issues = check_same_files_by_diff_study_ids(study_obj.name, study_obj.internal_id, study_obj.accession_number, filters)
        diff_files_problems.extend(issues)
    print "Ran check on the list of files retrieved by each study identifier -- result is: " + str(diff_files_problems)

    header_meta_needed = is_header_metadata_needed(args)
    irods_meta_needed = is_irods_metadata_needed(args)

    #i = 0
    all_h_samples = set()
    all_h_libraries = set()
    all_i_samples_by_names = set()
    all_i_samples_by_egaids = set()

    all_i_libraries_by_ids = set()
    all_i_libraries_by_names = set()

    all_i_studies_by_egaids = set()
    all_i_studies_by_names = set()


    all_problems = []
    issues_per_file = {}
    for f in filtered_fpaths:
        problems = []
        if args.config_file:
            pass


        # Retrieve the resources as needed in preparation for the tests:
        h_meta = None
        if header_meta_needed:
            try:
                header = metadata_utils.HeaderUtils.get_parsed_header_from_irods_file(f)
            except IOError as e:
                problems.append(str(e))
                continue
            else:
                h_meta = header_meta_module.HeaderSAMFileMetadata.from_header_to_metadata(header, f)
                sanity_issues = h_meta.run_field_sanity_checks_and_filter()
                problems.extend(sanity_issues)

                # populate the samples and libraries for outputting them (in case someone asked for them)
                all_h_samples.update(header.rg.samples)
                all_h_libraries.update(header.rg.libraries)

        if irods_meta_needed:
            irods_avus = metadata_utils.iRODSiCmdsUtils.retrieve_irods_avus(f)
            avu_issues = irods_meta_module.IrodsSeqFileMetadata.run_avu_count_checks(f, irods_avus)
            problems.extend(avu_issues)

            i_meta = irods_meta_module.IrodsSeqFileMetadata.from_avus_to_irods_metadata(irods_avus, f)
            ichksum_md5 = icommands_wrapper.iRODSChecksumOperations.get_checksum(f)
            i_meta.ichksum_md5 = ichksum_md5

            # Check for sanity before starting the tests:
            sanity_issues = i_meta.run_field_sanity_checks_and_filter()
            problems.extend(sanity_issues)

            # populate the samples and libraries for outputting them (in case someone asked for them)
            all_i_samples_by_names.update(i_meta.samples.get('name'))
            all_i_samples_by_egaids.update(i_meta.samples.get('accession_number'))

            all_i_libraries_by_names.update(i_meta.libraries.get('name'))
            all_i_libraries_by_ids.update(i_meta.libraries.get('internal_id'))

            all_i_studies_by_names.update(i_meta.studies.get('name'))
            all_i_studies_by_egaids.update(i_meta.studies.get('accession_number'))


            ## Filter by manual_qc:
            if not args.filter_npg_qc is None:
                if args.filter_npg_qc != i_meta.npg_qc:
                    continue


            ####### RUN THE TESTS: #########
            # MD5 tests:
            if args.test_md5 or args.all_tests:
                try:
                    i_meta.test_md5_calculated_vs_metadata()
                except (error_types.WrongMD5Error, error_types.TestImpossibleToRunError) as e:
                    problems.append(str(e))

            # TODO - not working properly
            if args.desired_reference or args.all_tests:
                try:
                    i_meta.test_reference(args.desired_reference)
                except (error_types.WrongReferenceError, error_types.TestImpossibleToRunError) as e:
                    problems.append(str(e))

            if args.test_filename or args.all_tests:
                try:
                    i_meta.test_lane_from_fname_vs_metadata()
                except (error_types.IrodsMetadataAttributeVsFileNameError, error_types.TestImpossibleToRunError) as e:
                    problems.append(str(e))

                try:
                    i_meta.test_run_id_from_fname_vs_metadata()
                except (error_types.IrodsMetadataAttributeVsFileNameError, error_types.TestImpossibleToRunError) as e:
                    problems.append(str(e))

                # TODO : test also the tag

            if args.test_sample or args.all_tests:
                if 'all' in args.test_sample or args.all_tests:
                    issues = check_irods_vs_header_metadata(f, h_meta.samples, i_meta.samples, 'sample')
                    problems.extend(issues)

                    issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.samples, 'sample')    #def compare_entity_sets_in_seqsc(entities_dict, entity_type):
                    problems.extend(issues)

                    issues = seq_consistency_checks.check_sample_is_in_desired_study(i_meta.samples['internal_id'], i_meta.studies['name'])
                    problems.extend(issues)
                else:
                    if 'irods_vs_header' in args.test_sample:
                        issues = check_irods_vs_header_metadata(f, h_meta.samples, i_meta.samples, 'sample')
                        problems.extend(issues)

                    if 'irods_vs_seqsc' in args.test_sample:
                        issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.samples, 'sample')    #def compare_entity_sets_in_seqsc(entities_dict, entity_type):
                        problems.extend(issues)

                        issues = seq_consistency_checks.check_sample_is_in_desired_study(i_meta.samples['internal_id'], i_meta.studies['name'])
                        problems.extend(issues)

            if args.test_library or args.all_tests:
                if args.all_tests or 'all' in args.test_library:
                    issues = check_irods_vs_header_metadata(f, h_meta.libraries, i_meta.libraries, 'library')
                    problems.extend(issues)

                    issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.libraries, 'library')
                    problems.extend(issues)
                else:
                    if 'irods_vs_header' in args.test_library:
                        issues = check_irods_vs_header_metadata(f, h_meta.libraries, i_meta.libraries, 'library')
                        problems.extend(issues)

                    if 'irods_vs_seqsc' in args.test_library:
                        issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.libraries, 'library')
                        problems.extend(issues)


            if args.test_study or args.all_tests:
                issues = seq_consistency_checks.compare_entity_sets_in_seqsc(i_meta.studies, 'study')
                problems.extend(issues)


            if args.all_tests or args.test_complete_meta:
                # TODO: Add a warning that by default there is a default config file used
                if not args.config_file:
                    config_file = config.IRODS_ATTRIBUTE_FREQUENCY_CONFIG_FILE
                else:
                    config_file = args.config_file
                try:
                    diffs = complete_irods_metadata_checks.check_avus_freq_vs_config_freq(irods_avus, config_file)
                except IOError:
                    problems.append(error_types.TestImpossibleToRunError(f, "Test iRODS metadata is complete",
                                                                         "Config file missing: "+str(config_file)))
                else:
                    diffs_as_exc = complete_irods_metadata_checks.from_tuples_to_exceptions(diffs)
                    for d in diffs_as_exc:
                        d.fpath = f
                    problems.extend(diffs_as_exc)

        print "FILE: " + str(f) + " -- PROBLEMS found: " + str(problems)
        if problems:
            issues_per_file[f] = problems
        #
        # i += 1
        # if i == 10:
        #     sys.exit()
        all_problems.extend(problems)

    print "NUMBER OF FILES WITH ISSUES: " + str(len(issues_per_file))
    # PRINT OUTPUT:
    # FILES EXCLUDED:
    # TODO: add an option in which you see also the files that were filtered out
    print "FILES FILTERED OUT: "
    for reason,files in files_excluded.iteritems():
        print "REASON: " + str(reason)
        for f_excl in files:
            str(f_excl)

    print "DIFFERENT FILES RETRIEVED BY QUERYING BY DIFF STUDY IDS: "
    for err in all_problems:
        if type(err) is error_types.DifferentFilesRetrievedByDiffStudyIdsOfSameStudy:
            print "Number of files retrieved when querying by: " + err.id1 + " and " + err.id2 + " = " + str(len(err.diffs))


    # # OUTPUTS
    if args.fofn_probl:
        write_list_to_file(issues_per_file.keys(), args.fofn_probl)


    ######## OUTPUT ENTITIES #######################
    study_name_as_ascii = args.study
    if args.study:
        study_name_as_ascii = ''.join([i if (ord(i) < 128 and ord(i) >= 65) or i == '_' else '' for i in args.study])

    out_dir = ''
    if args.entities_out_dir:
        out_dir = args.entities_out_dir
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)


    HEADER_SAMPLE_IDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.header.sample.ids')
    HEADER_LIBRARY_IDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.header.library.ids')
    IRODS_SAMPLE_NAMES_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.sample.names')
    IRODS_SAMPLE_EGAIDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.sample.egaids')
    IRODS_LIBRARY_NAMES_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.library.names')
    IRODS_LIBRARY_IDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.library.ids')
    IRODS_STUDY_NAMES_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.study.names')
    IRODS_STUDY_EGAIDS_FILE = os.path.join(out_dir, study_name_as_ascii + '.irods.study.egaids')

    ALL_ENTITIES_FILE = os.path.join(out_dir, study_name_as_ascii + '.entities.txt')

    FILE_OF_FNAMES_BY_FTYPES = os.path.join(study_name_as_ascii + '.fnames_by_ftypes.txt')

    ############ OUTPUT HEADER METADATA ############
    # outputting HEADER samples:
    if args.header_sample_ids_file:
        #write_list_to_file(all_h_samples, args.header_sample_ids_file)
        write_list_to_file(all_h_samples, HEADER_SAMPLE_IDS_FILE)

    # outputting HEADER libraries:
    if args.header_library_ids_file:
        #write_list_to_file(all_h_libraries, args.header_library_ids_file)
        write_list_to_file(all_h_libraries, HEADER_LIBRARY_IDS_FILE)

    ############ OUTPUT IRODS METADATA ###############
    # outputting IRODS samples by EGA ID:
    if args.sample_ega_out_file:
#        write_list_to_file(all_i_samples_by_egaids, args.sample_ega_out_file)
        write_list_to_file(all_i_samples_by_egaids, IRODS_SAMPLE_EGAIDS_FILE)


    # outputting iRODS samples by name
    if args.sample_names_out_file:
#        write_list_to_file(all_i_samples_by_names,args.sample_names_out_file)
        write_list_to_file(all_i_samples_by_names, IRODS_SAMPLE_NAMES_FILE)

    # outputting iRODS libraries by id
    if args.library_ids_out_file:
#        write_list_to_file(all_i_libraries_by_ids, args.library_ids_out_file)
        write_list_to_file(all_i_libraries_by_ids, IRODS_LIBRARY_IDS_FILE)

    #outputting iRODS libraries by name
    if args.library_names_out_file:
#        write_list_to_file(all_i_libraries_by_names,args.library_names_out_file)
        write_list_to_file(all_i_libraries_by_names, IRODS_LIBRARY_NAMES_FILE)

    ##### STUDIES #####
    # outputting IRODS studies by ega id:
    if args.study_egaids_out_file:
#        write_list_to_file(all_i_studies_by_egaids, args.study_egaids_out_file)
        write_list_to_file(all_i_studies_by_egaids, IRODS_STUDY_EGAIDS_FILE)

    # outputting IRODS studies by name:
    if args.study_names_out_file:
#        write_list_to_file(all_i_studies_by_names, args.study_names_out_file)
        write_list_to_file(all_i_studies_by_names, IRODS_STUDY_NAMES_FILE)


    ##################  OUTPUTTING ALL THE ENTITIES ########################

    if args.entities_out_file:
        write_list_to_file([len(all_i_samples_by_names), len(all_i_samples_by_egaids), len(all_h_samples), len(all_i_libraries_by_names), len(all_h_libraries)],
                           ALL_ENTITIES_FILE, header="Irods_sample_names\tIrods_sample_egaids\tHeader_samples\tIrods_library_names\tHeader_libraries")
        write_list_to_file(all_h_samples, ALL_ENTITIES_FILE, header="HEADER SAMPLES")
        write_list_to_file(all_h_libraries, ALL_ENTITIES_FILE, header="HEADER LIBRARIES")
        write_list_to_file(all_i_samples_by_egaids, ALL_ENTITIES_FILE, header="IRODS SAMPLES BY EGA ID")
        write_list_to_file(all_i_samples_by_names, ALL_ENTITIES_FILE, header="IRODS SAMPLES BY NAME")
        write_list_to_file(all_i_libraries_by_ids, ALL_ENTITIES_FILE, header="IRODS LIBRARIES BY ID")
        write_list_to_file(all_i_libraries_by_names, ALL_ENTITIES_FILE, header="IRODS LIBRARIES BY NAME")
        write_list_to_file(all_i_studies_by_egaids, ALL_ENTITIES_FILE, header="IRODS STUDIES BY EGA ID")
        write_list_to_file(all_i_studies_by_names, ALL_ENTITIES_FILE, header="IRODS STUDIES BY NAME")


    #### OUTPUTTING the files by type ############
    # Count nr of files per type and build the sorted dict:
    counter_by_ftype = defaultdict(int)
    files_sorted_by_type = defaultdict(dict)  # dict of key = file name (no ext), value = dict - of type : fpath
    for f in filtered_fpaths:
        fname = utils.extract_fname_without_ext(f)
        ftype = infer_file_type(f)
        files_sorted_by_type[fname][ftype] = f
        counter_by_ftype[ftype] += 1

    # printing out the count of files per format:
    for format, n in counter_by_ftype.items():
        print "format = " + str(format) + " nr files = " + str(n)


    if args.fnames_by_ftype:
        # Going through the sorted files by type and put them in tuples
        ftypes_tuples = []
        wanted_ftypes = args.file_types
        for fname, ftypes_dict in files_sorted_by_type.items():
            ftyptes_per_fname = []
            for wanted_ft in wanted_ftypes:
                fpath_per_type = ftypes_dict.get(wanted_ft) or 'missing'
                ftyptes_per_fname.append(fpath_per_type)
            ftypes_tuples.append(ftyptes_per_fname)
        write_tuples_to_file(ftypes_tuples, FILE_OF_FNAMES_BY_FTYPES, wanted_ftypes)


        # Analyze the sorted dict to test that it all looks fine:
        missing_ftypes_errors = []
        for fname, files in files_sorted_by_type.items():
            existing_ftypes = set()
            wanted_ftypes = set(args.file_types)
            for f in files:
                ftype = infer_file_type(f)
                existing_ftypes.add(ftype)

            # CHeck if the existing file types are the wanted ones...
            if wanted_ftypes != existing_ftypes:
                missing_ftypes = wanted_ftypes.difference(existing_ftypes)
                missing_ftypes_errors.append(error_types.MissingFileFormatsFromIRODSError(fname, missing_ftypes))

        for error in missing_ftypes_errors:
            print str(error)





    ## FILTER OUTPUT depending on what params were given (what was asked as output)

    ## PUT THE OUTPUT IN REQUESTED FORMAT


if __name__ == '__main__':
    main()


