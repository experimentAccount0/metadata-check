"""
Copyright (C) 2016  Genome Research Ltd.

Author: Irina Colgiu <ic4@sanger.ac.uk>

This program is part of meta-check

meta-check is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.
You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

This file has been created on May 20, 2016.
"""


class CHECK_NAMES:
    valid_replica_checksum_check = "Check that the replica checksum field is valid"
    valid_replica_number_check = "Check that the replica number is valid"
    attribute_count_check = "Check attribute count is as configured"
    check_all_replicas_same_checksum = "Check all replicas have the same checksum"
    check_more_than_one_replica = "Check that file has more than 1 replica"
    check_no_public_acl = "Check that there are no public ACLS"
    check_ss_irods_group_read_permission = "Check that the permission for iRODS ss_<id> user group is READ"
    check_there_is_ss_irods_group = "Check ACLs contain at least one ss_<id> group"
    check_checksum_in_metadata_present = "Check that checksum present within metadata"
    check_checksum_at_upload_present = "Check that checksum at upload(ichksum) present"
    check_by_comparison_checksum_in_meta_with_checksum_at_upload = "Compare checksum in metadata with checksum at upload"
    check_npg_qc_field = "Check that the NPG QC field is valid"
    check_target_field = "Check that the target field is valid"
    check_desired_reference = "Check that the reference for this file is the one desired"
    check_irods_zone_within_acl = "Check valid iRODS zone in ACL"
    check_irods_permission_within_acl = "Check valid permission in ACL"
    check_valid_ids = "Check valid id strings"
    check_all_irods_ids_found_in_seqscape = "Check all iRODS ids were found in seqscape"
    check_for_duplicated_ids_within_seqscape = "Check for duplicated ids within seqscape"
    check_entities_in_seqscape_fetched_by_different_ids = "Check entities fetched by different types of ids from Seqscape"
    check_samples_belong_to_same_study = "Check the samples belong to the same studies in iRODS and Seqscape"
    check_that_the_given_study_is_associated_with_the_known_samples = "Check that given the study in iRODS, the samples in iRODS are associated with it"
    check_studies_in_irods_with_studies_in_seqscape_fetched_by_samples = "Check that the studies in iRODS are the same as the studies fetched from Seqscape when querying by sample"
    check_samples_in_irods_same_as_samples_fetched_by_study_from_seqscape = "Check that the samples in iRODS are the same as the samples fetched by study from Seqscape"
    check_for_samples_in_more_studies = "Check if a set of samples is in more studies within Seqscape"
    check_all_id_types_present = 'Check that all id types are present'


