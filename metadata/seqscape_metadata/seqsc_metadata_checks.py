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

This file has been created on Nov 10, 2015.
"""

from typing import List
import collections

from main import error_types
from seqscape import queries as seqsc_q
from metadata.seqscape_metadata.seqscape_metadata import SeqscapeRawMetadata, SeqscapeEntitiesFetched


class SeqscapeFetchedEntitiesChecks:
    @classmethod
    def _find_missing_ids(cls, ids_found: List[str], ids_given: List[str]):
        return set(ids_given).difference(set(ids_found))

    @classmethod
    def _find_duplicated_ids(cls, ids_found: List[str]):
        return [item for item, count in collections.Counter(ids_found).items() if count > 1]

    @classmethod
    def check_all_ids_were_found(cls, entities_fetched_obj: SeqscapeEntitiesFetched):
        ids_found = [str(getattr(ent, entities_fetched_obj.query_id_type)) for ent in
                     entities_fetched_obj.entities_fetched]
        ids_missing = cls._find_missing_ids(ids_found, entities_fetched_obj.query_ids)
        if ids_missing:
            raise error_types.NotFoundInSeqscapeError(entities_fetched_obj.query_id_type, ids_missing,
                                                      entities_fetched_obj.query_entity_type)

    @classmethod
    def check_no_duplicates_found(cls, entities_fetched_obj: SeqscapeEntitiesFetched):
        ids_found = [getattr(ent, entities_fetched_obj.query_id_type) for ent in entities_fetched_obj.entities_fetched]
        ids_duplicated = cls._find_duplicated_ids(ids_found)
        entities_dupl_ids = [ent for ent in entities_fetched_obj.entities_fetched
                             if getattr(ent, entities_fetched_obj.query_id_type) in ids_duplicated]
        if ids_duplicated:
            raise error_types.TooManyEntitiesSameIdSeqscapeError(entities_fetched_obj.query_id_type, ids_duplicated,
                                                                 entities_dupl_ids)


class SeqscapeRawMetadataChecks(object):

    @classmethod
    def _compare_entity_sets(cls, entities_list: List[SeqscapeEntitiesFetched]) -> List[
        error_types.DiffEntitiesRetrievedFromSeqscapeByDiffIdTypesError]:
        problems = []
        for i in range(1, len(entities_list) - 1):
            if not set(entities_list[i - 1].entities_fetched) == set(entities_list[i].entities_fetched):
                problems.append(error_types.DiffEntitiesRetrievedFromSeqscapeByDiffIdTypesError(
                    entity_type=entities_list[i].entity_type,
                    id_type1=entities_list[i].query_id_type,
                    id_type2=entities_list[i - 1].query_id_type,
                    entities_set1=entities_list[i - 1].entities_fetched,
                    entities_set2=entities_list[i].entities_fetched
                ))
        return problems

    @classmethod
    def check_entities_fetched_by_different_id_types(cls, fetched_entities_list: List[SeqscapeEntitiesFetched]) -> None:
        return cls._compare_entity_sets(fetched_entities_list)


    @classmethod
    def check_entities_fetched(cls, entities_fetched_list: List[SeqscapeEntitiesFetched]) -> None:
        for entity_fetched in entities_fetched_list:
            SeqscapeFetchedEntitiesChecks.check_all_ids_were_found(entity_fetched)
            SeqscapeFetchedEntitiesChecks.check_no_duplicates_found(entity_fetched)

    # @classmethod
    # def check_all_fetched_entities_in_raw_metadata(cls, raw_meta: SeqscapeRawFetchedMetadata) -> None:


    def check_samples_belong_to_studies_given(self, seqscape_meta: SeqscapeRawMetadata) -> None:
        studies_by_samples = seqsc_q.query_for_studies_by_samples(seqscape_meta.samples)


        # actual_studies_from_seqsc = seqsc.query_for_studies_by_samples(sample_ids)
        # studies_by_name = [s.name for s in actual_studies_from_seqsc]
        # if study_name not in studies_by_name:
        # return error_types.SamplesDontBelongToGivenStudy(sample_ids=sample_ids, actual_study=str(studies_by_name), desired_study=study_name)
        #

    @classmethod
    def check_raw_metadata(cls, raw_metadata: SeqscapeRawMetadata) -> None:
        """
        Checks the raw metadata and throws exceptions if any problem is found
        :param raw_metadata:
        :return:
        """
        entity_types = raw_metadata.get_all_fetched_entity_types()
        for entity_type in entity_types:
            entities_fetched = raw_metadata.get_fetched_entities_by_type(entity_type)
            cls.check_entities_fetched(entities_fetched)
            cls.check_entities_fetched_by_different_id_types(entities_fetched)


