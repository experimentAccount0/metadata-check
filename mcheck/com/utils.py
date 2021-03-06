"""
Copyright (C) 2013, 2014  Genome Research Ltd.

Author: Irina Colgiu <ic4@sanger.ac.uk>

This program is part of metadata-check.

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

"""

import os
import time
import unicodedata
import datetime
import collections
import string

from os.path import isfile, join
from collections import defaultdict


#################################################################################
from mcheck.com import wrappers

'''
 This class contains small utils functions, for general purpose and not specific
 to the controller side or the workers side.
'''
#################################################################################

########################## GENERAL USE FUNCTIONS ################################



######################### JSON CONVERSION #######################################
#
#
#def serialize(data):
#    return simplejson.dumps(data)
#
#
#def deserialize(data):
#    return simplejson.loads(data)


############## FILE NAME/PATH/EXTENSION PROCESSING ###########

def read_file_into_list(fofn_path):
    fofn_fd = open(fofn_path)
    files_list = [f.strip() for f in fofn_fd]
    fofn_fd.close()
    return files_list


def write_list_to_file(input_list, output_file, header=None):
    out_fd = open(output_file, 'a')
    if header:
        out_fd.write(header + '\n')
    for entry in input_list:
        out_fd.write(str(entry) + '\n')
    out_fd.write('\n')
    out_fd.close()


def write_tuples_to_file(tuples, output_file, header_tuple=None):
    out_fd = open(output_file, 'a')
    for elem in header_tuple:
        out_fd.write(str(elem) + "\t")
    out_fd.write("\n")
    for tup in tuples:
        for elem in tup:
            out_fd.write(str(elem) + "\t")
        out_fd.write("\n")
    out_fd.close()


def write_dict_to_file(input_dict, output_file, header=None):
    out_fd = open(output_file, 'a')
    if header:
        out_fd.write(header + "\n")
    for k, v in input_dict.items():
        out_fd.write(str(k))
        out_fd.write("\n")
        out_fd.write(str(v))
        out_fd.write("\n")
    out_fd.close()


def extract_fname_and_ext(fpath):
    ''' This function splits the filename in its last extension
        and the rest of it. The name might be confusion, as for
        files with multiple extensions, it only separates the last
        one from the rest of them. 
        e.g. UC123.bam.bai.md5 => fname=UC123.bam.bai, ext=md5
    '''
    _, tail = os.path.split(fpath)
    fname, ext = os.path.splitext(tail)
    ext = ext[1:]
    return (fname, ext)

@wrappers.check_args_not_none
def extract_fname(fpath):
    _, fname = os.path.split(fpath)
    return fname

@wrappers.check_args_not_none
def extract_fname_without_ext(fpath):
    ''' Extracts the file name (and removes the extensions), given a file path.'''
    #_, fname = os.path.split(fpath)
    fname = extract_fname(fpath)
    basename, _ = os.path.splitext(fname)
    return basename

@wrappers.check_args_not_none
def extract_dir_path(fpath):
    ''' Extracts the root directory from a filepath.'''
    if os.path.isdir(fpath):
        return fpath
    return os.path.dirname(fpath)

#def extract_file_extension(fpath):
#    _, tail = os.path.split(fpath)
#    _, ext = os.path.splitext(tail)
#    return ext[1:]
# 
    
    
def list_and_filter_files_from_dir(dir_path, accepted_extensions):
    ''' This function returns all the files of the types of interest 
        (e.g.bam, vcf, and ignore .txt) from a directory given as parameter.
    '''
    files_list = []
    for f_name in os.listdir(dir_path):
        f_path = join(dir_path, f_name)
        if isfile(f_path):
            _, f_extension = os.path.splitext(f_path)
            if f_extension[1:] in accepted_extensions:
                files_list.append(f_path)
    print(files_list)
    return files_list

@wrappers.check_args_not_none
def get_filename_from_path(fpath):
    if fpath in ["\n", " ","","\t"]:
        raise ValueError("File path empty")
    f_path = fpath.lstrip().strip()
    return os.path.basename(f_path)

@wrappers.check_args_not_none
def get_filepaths_from_fofn(fofn):
    files_list = [f for f in open(fofn, 'r')]
    return [_f for _f in files_list if _f]


def get_filenames_from_filepaths(filepaths_list):
    return [get_filename_from_path(file_path) for file_path in filepaths_list]


def filter_list_of_files_by_type(list_of_files, filters):
    ''' Filters the initial list of files and returns a new list of files
        containing only the file types desired (i.e. given as filters parameter).
    '''
    files_filtered = []
    for f in list_of_files:
        _, tail = os.path.split(f)
        _, ext = os.path.splitext(tail)
        ext = ext[1:]
        if ext in filters:
            files_filtered.append(f)
        else:
            print("SMTH else in this dir:",f)
    return files_filtered

@wrappers.check_args_not_none
def extract_file_extension(fpath):
    if not fpath:
        return None
    _, tail = os.path.split(fpath)
    _, ext = os.path.splitext(tail)
    return ext[1:].strip()


def lists_contain_same_elements(list1, list2):
        return set(list1) == set(list2)



#################### PROJECT SPECIFIC UTILITY FUNCTIONS #####################


def filter_out_invalid_paths(file_paths_list):
    return [fpath for fpath in file_paths_list if fpath not in [None, ' ', '']]
    

def get_file_duplicates(files_list):
    if len(files_list)!=len(set(files_list)):
        return [x for x, y in list(collections.Counter(files_list).items()) if y > 1]
    return []


def list_fullpaths_from_dir(path):
    ''' Throws a ValueError if the dir doesn't exist or the path 
        is not a dir or if the dir is empty. 
        Returns the list of files from that dir.
    '''
    return [join(path, fname) for fname in os.listdir(path)]


def split_path_in_components(path):
    folders=[]
    while 1:
        path,folder=os.path.split(path)
    
        if folder!="":
            folders.append(folder)
        else:
            if path!="":
                folders.append(path)
            break
    folders.reverse()
    return folders


def get_all_file_types(fpaths_list):
    ''' 
        This function receives a list of file paths as argument and extracts
        from it a set of all the files types of the files in the list. 
    '''
    file_types = set()
    for f in fpaths_list:
        ext = extract_file_extension(f)
        if ext:
            file_types.add(ext)
    return file_types


def filter_out_none_keys_and_values(my_dict):
    return {k:v for (k,v) in my_dict.items() if k is not None and v is not None}

def check_all_keys_have_the_same_value(my_dict, my_value=None):
        if my_value:
            return all(val==my_value for val in list(my_dict.values()))
        return len(set(my_dict.values()))==1
    

###########################################################################


def is_field_empty(obj, field):
    return not (hasattr(obj, field) and getattr(obj, field) != None)


def is_date_correct(date):
    try:
        date_struct = time.strptime(date, "%Y-%m-%d")
    except ValueError:
        # Only caught the error to change the message with a more relevant one
        raise ValueError("Error: date is not in the correct format.")
    year = date_struct.tm_year
    print(year)
    max_year = datetime.date.today().year
    if int(year) < 2010:
        raise ValueError("The year given is incorrect. Min year = 2013")
    if int(year) > max_year:
        raise ValueError("The year given is incorrect. Max year = "+str(max_year))
    return True
        

############## OTHER GENERAL UTILS ################

def get_today_date():
    today = datetime.date.today()
    return today.isoformat()

def get_date_and_time_now():
    return time.strftime("%H:%M on %d/%m/%Y")
    
    
def is_hexadecimal_string(s):
    return all(c in string.hexdigits for c in s)

def levenshtein(a,b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = list(range(n+1))
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]


############################# ADJACENT THINGS -- PROBABLY SHOULD BE HERE!!! Until I think things through and try diff options ###########

@wrappers.check_args_not_none
def compare_strings(str1, str2):
    ''' Compares two strings and returns True if they are identical, False if not.'''
    return str1 == str2
    
    
def compare_strings_ignore_case(str1, str2):
    ''' Compares two strings ignoring the case. Returns True if they match, False if not.'''
    return compare_strings(str1.lower(), str2.lower())


def get_key_counts(tuples_list):
    ''' 
        This function calculates the number of occurences of
        each key in the list of tuples received as parameter.
        Returns a dict containing: key - occurances.
    '''
    key_freq_dict = defaultdict(int)
    for item in tuples_list:
        key_freq_dict[item[0]] += 1
    return key_freq_dict


    
    
    
