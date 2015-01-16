# Copyright (C) 2014  Roman Zimbelmann <hut@hut.pm>
# This software is distributed under the terms of the GNU GPL version 3.

"""
A Metadata Manager that reads information about files from a json database.

The database is contained in a local .metadata.json file.
"""

METADATA_FILE_NAME = ".metadata.json"
DEEP_SEARCH_DEFAULT = False

import copy
from os.path import join, dirname, exists, basename
from ranger.ext.openstruct import OpenStruct

class MetadataManager(object):
    def __init__(self):
        self.metadata_cache = dict()
        self.metafile_cache = dict()
        self.deep_search = DEEP_SEARCH_DEFAULT

    def reset(self):
        self.metadata_cache.clear()
        self.metafile_cache.clear()

    def get_metadata(self, filename):
        try:
            return copy.deepcopy(self.metadata_cache[filename])
        except KeyError:
            result = OpenStruct(filename=filename, title=None, year=None,
                    authors=None, url=None)

            valid = (filename, basename(filename))
            for metafile in self._get_metafile_names(filename):

                # Iterate over all the entries in the given metadata file:
                for entries in self._get_metafile_content(metafile):
                    # Check for a direct match:
                    if filename in entries:
                        entry = entries[filename]
                    # Check for a match of the base name:
                    elif basename(filename) in entries:
                        entry = entries[basename(filename)]
                    else:
                        # No match found, try another entry
                        continue

                    entry = OpenStruct(entry)
                    self.metadata_cache[filename] = entry
                    return copy.deepcopy(entry)

            # Cache the value
            self.metadata_cache[filename] = result
            return result

    def set_metadata(self, filename, update_dict):
        import json
        result = None
        found = False
        valid = (filename, basename(filename))
        first_metafile = None

        if not self.deep_search:
            metafile = next(self._get_metafile_names(filename))
            return self._set_metadata_raw(filename, update_dict, metafile)

        for i, metafile in enumerate(self._get_metafile_names(filename)):
            if i == 0:
                first_metafile = metafile

            csvfile = None
            try:
                csvfile = open(metafile, "r")
            except:
                # .metadata.json file doesn't exist... look for another one.
                pass
            else:
                reader = csv.reader(csvfile, skipinitialspace=True)
                for row in reader:
                    name, year, title, authors, url = row
                    if name in valid:
                        return self._set_metadata_raw(filename, update_dict,
                                metafile)
                self.metadata_cache[filename] = result
            finally:
                if csvfile:
                    csvfile.close()

        # No .metadata.json file found, so let's create a new one in the same
        # path as the given file.
        if first_metafile:
            return self._set_metadata_raw(filename, update_dict, first_metafile)

    def _set_metadata_raw(self, filename, update_dict, metafile):
        import json
        valid = (filename, basename(filename))
        metadata = OpenStruct(filename=filename, title=None, year=None,
                authors=None, url=None)

        try:
            with open(metafile, "r") as infile:
                reader = csv.reader(infile, skipinitialspace=True)
                rows = list(reader)
        except IOError:
            rows = []

        with open(metafile, "w") as outfile:
            writer = csv.writer(outfile)
            found = False

            # Iterate through all rows and write them back to the file.
            for row in rows:
                if not found and row[0] in valid:
                    # When finding the row that corresponds to the given filename,
                    # update the items with the information from update_dict.
                    self._fill_row_with_ostruct(row, update_dict)
                    self._fill_ostruct_with_data(metadata, row)
                    self.metadata_cache[filename] = metadata
                    found = True
                writer.writerow(row)

            # If the row was never found, create a new one.
            if not found:
                row = [basename(filename), None, None, None, None]
                self._fill_row_with_ostruct(row, update_dict)
                self._fill_ostruct_with_data(metadata, row)
                self.metadata_cache[filename] = metadata
                writer.writerow(row)

    def _get_metafile_content(self, metafile):
        import json
        if metafile in self.metafile_cache:
            return self.metafile_cache[metafile]
        else:
            if exists(metafile):
                with open(metafile, "r") as f:
                    entries = json.load(f)
                self.metafile_cache[metafile] = entries
                return entries
            else:
                return {}

    def _get_metafile_names(self, path):
        # Iterates through the paths of all .metadata.json files that could
        # influence the metadata of the given file.
        # When deep_search is deactivated, this only yields the .metadata.json
        # file in the same directory as the given file.

        base = dirname(path)
        yield join(base, METADATA_FILE_NAME)
        if self.deep_search:
            dirs = base.split("/")[1:]
            for i in reversed(range(len(dirs))):
                yield join("/" + "/".join(dirs[0:i]), METADATA_FILE_NAME)

    def _fill_ostruct_with_data(self, ostruct, dataset):
        # Copy data from a CSV row to a dict/ostruct

        filename, year, title, authors, url = dataset
        if year:    ostruct['year']    = year
        if title:   ostruct['title']   = title
        if authors: ostruct['authors'] = authors
        if url:     ostruct['url']     = url

    def _fill_row_with_ostruct(self, row, update_dict):
        # Copy data from a dict/ostruct into a CSV row
        for key, value in update_dict.items():
            if key == "year":
                row[1] = value
            elif key == "title":
                row[2] = value
            elif key == "authors":
                row[3] = value
            elif key == "url":
                row[4] = value
