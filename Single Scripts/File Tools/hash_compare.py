"""
Description: 
Compares and matches hash values of files in two directories.
Outputs a list-dict of matches (dir1 to dir2).

Version: 1.0.0
Created: 07/30/2024
Created by: Tanner Hammond
Python Version: 3.11.8
"""

import hashlib
import os.path
from typing import Union

HASHTYPES = {'sha1':hashlib.sha1(),'sha224':hashlib.sha224(),'sha256':hashlib.sha256(),'sha384':hashlib.sha384(),'sha512':hashlib.sha512(),'sha3_224':hashlib.sha3_224(),
             'sha3_256':hashlib.sha3_224(),'sha3_384':hashlib.sha3_384(),'sha3_512':hashlib.sha3_512(),'shake_128':hashlib.shake_128(),'shake_256':hashlib.shake_256(),
             'blake2b':hashlib.blake2b(),'blake2s':hashlib.blake2s(),'md5':hashlib.md5()}

def hash_file(path: Union[str|os.PathLike], method: str = 'sha256', chunk_size: int = 4096) -> str:
    """
    Hashes a single file and returns a hash value string.

    Params:
    * `path`: File path of file that will be hashed.
    * `method`: Hashing method to be used. All hash types in `hashlib` as of writing are available.
        * Default: `'ssha256'`
        * Accepted Values: See `HASHTYPES` constant.
    * `chunk_size`: Size parameter for `file.read()`.
        * Default: `4096`
    """

    hasher = HASHTYPES[method]
    if hasher is None:
        raise ValueError(f'"{method}" is not a valid hashing method. Possible methods: {*HASHTYPES,}.')
    with open(path, 'rb') as file:
        for chunk in iter(lambda: file.read(chunk_size), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def dir_hash_compare(dir1: Union[str|os.PathLike], dir2: Union[str|os.PathLike], method: str = 'sha256', chunk_size: int = 4096) -> list:
    '''
    Compares hash values of files in two directories. Values in the second directory are matched to the first but not vice versa.

    Params:
    * `dir1`: First file directory.
    * `dir2`: Second file directory.
    * `method`: Hash method to use.
        * Default: `"sha256"`
    * `chunk_size`: Hash chunk size.
    '''
    #Get All File Paths
    dir1_files = [os.path.join(root, path) for root, _, paths in os.walk(dir1) for path in paths]
    dir2_files = [os.path.join(root, path) for root, _, paths in os.walk(dir2) for path in paths]

    #Hash Files in First Directory
    dir1_hashes = {}
    for file in dir1_files:
        hash_value = hash_file(file, method, chunk_size)
        if hash_value in dir1_hashes:
            dir1_hashes[hash_value].append(file)
        else:
            dir1_hashes[hash_value] = [file]

    #Hash Files in Second Directory
    dir2_hashes = {}
    for file in dir2_files:
        hash_value = hash_file(file, method, chunk_size)
        if hash_value in dir2_hashes:
            dir2_hashes[hash_value].append(file)
        else:
            dir2_hashes[hash_value] = [file]

    #Check Similarities
    matching_hashes = []
    for hash_ in dir1_hashes:
        if hash_ in dir2_hashes:
            matching_hashes.append({'hash':hash_,'dir1files':dir1_hashes[hash_],'dir2files':dir2_hashes[hash_]})
        else:
            matching_hashes.append({'hash':hash_,'dir1files':dir1_hashes[hash_],'dir2files':None})
    
    return matching_hashes


#Usage -----
directory1 = 'C:/path/to/dir1'
directory2 = 'C:/path/to/dir2'
hash_method = 'sha256'
chunk = 4096

hash_comparison = dir_hash_compare(directory1, directory2, hash_method, chunk)