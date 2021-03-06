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

This file has been created on Jun 30, 2015.
"""

#from . import error_types
import typing
from mcheck.check_names import CHECK_NAMES
from mcheck.metadata.common.comparable_metadata import ComparableMetadata
from mcheck.results.checks_results import RESULT

from mcheck.results.checks_results import CheckResult


class SAMFileHeaderMetadata(ComparableMetadata):
    INVALID_IDS = ['N/A', 'undefined', 'unspecified', -1, '', None]

    def __init__(self, fpath, samples={}, libraries={}, studies={}, reference=None, platforms=None):    # fname,
        self.fpath = fpath
        self.samples = samples
        self.libraries = libraries
        self.studies = studies
        self.reference = reference
        self.platforms = platforms


    @classmethod
    def _is_id_valid(cls, id: str) -> bool:
        return id not in cls.INVALID_IDS

    @classmethod
    def _filter_out_invalid_ids(cls, ids_list: typing.Sequence):
        return {id for id in ids_list if cls._is_id_valid(id)}

    @classmethod
    def _check_for_invalid_ids(cls, multi_ids_dict: typing.Dict, entity_type: str):
        check_result = CheckResult(check_name=CHECK_NAMES.check_valid_ids, error_message=[])
        if not multi_ids_dict:
            check_result.result = RESULT.FAILURE
            check_result.error_message.append("No ids found.")
        for k, values in multi_ids_dict.items():
            wrong_ids = [id for id in values if not cls._is_id_valid(id)]
            if wrong_ids:
                check_result.error_message.append("Invalid " + str(k) + "(s) for " + str(entity_type) + ": " + str(wrong_ids))
                check_result.result = RESULT.FAILURE
        return check_result

    def check_metadata(self):
        errors = []
        errors.append(self._check_for_invalid_ids(self.samples, 'sample'))
        errors.append(self._check_for_invalid_ids(self.libraries, 'library'))
        return errors

    def fix_metadata(self):
        for id_type, values in self.samples.items():
            fixed_values = self._filter_out_invalid_ids(values)
            self.samples[id_type] = fixed_values

        for id_type, values in self.libraries.items():
            fixed_values = self._filter_out_invalid_ids(values)
            self.libraries[id_type] = fixed_values
        return

    def __str__(self):
        return "Fpath = " + str(self.fpath) + ", samples = " + str(self.samples) + \
               ", libraries = " + str(self.libraries) + ", platforms = " + \
               str(self.platforms)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.fpath == other.fpath and self.samples == other.samples and \
               self.libraries == other.libraries and self.studies == other.studies and \
               self.reference == other.reference and self.platforms == other.platforms

class LaneletSAMFileHeaderMetadata(SAMFileHeaderMetadata):
    def __init__(self, fpath,  samples={}, libraries={}, studies={}, lanelets=None, reference=None, platforms=None):    # fname,
        super().__init__(fpath, samples, libraries, studies, reference, platforms)
        self.lanelets = lanelets

    def __str__(self):
        return super().__str__() + ", lanelets = " + str(self.lanelets)

    def __eq__(self, other):
        return super().__eq__(other) and self.lanelets == other.lanelets

