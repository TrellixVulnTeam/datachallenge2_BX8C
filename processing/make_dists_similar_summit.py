# For the Oak Ridge National Lab Data Challenge
# Challenge 2
# written by Emily Costa and Alvin Tan
# 08/02/2019

import os
import numpy as np
import h5py
import random
from pandas import DataFrame 
import json


def _convert_JSON_to_arr(JSON_path):
    with open(JSON_path, "r") as JSON_file:
        data = json.load(JSON_file)
        space_group_inds = list(range(1, 231))
        data = np.array([data['Space Group {}'.format(ind)] for ind in space_group_inds])

    return data


def _distribute_dataset(anH5File, h5Files, space_group_distribution):
    keys = list(anH5File.keys())
    #samples = [f[key] for key in keys]

    # Pseudorandomly distribute samples among the new files for a
    # roughly even distribution
    for key in keys:
        # if there are less than 30 total instances of this space group, 
        # we add them to all of the .h5 files
        if space_group_distribution[anH5File[key].attrs['space_group'] - 1] < 30:
            for h5File in h5Files:
                anH5File.copy(key, h5File)

        # Otherwise, we pseudorandomly distribute samples among the new files for a
        # roughly even distribution
        randNum = random.randrange(len(h5Files))
        anH5File.copy(key, h5Files[randNum])

    return


def _setup_h5_datasets(h5_save_path, fileNames, fileRatios):
    h5Files = []

    # Creates our new .h5 files to be filled out
    for i in range(len(fileNames)):
        filePath = "{}massaged{}.h5".format(h5_save_path, fileNames[i])
        newH5File = h5py.File(filePath)

        # We add the new file enough times to have the random distribution distribute
        # as desired. In essence, creating more bins to be uniformly distributed
        # over, but some of the bins are just one fat bin, so they catch more.
        for j in range(fileRatios[i]):
            h5Files.append(newH5File)
            
        print("Created new .h5 file at {}".format(filePath))

    return h5Files


if __name__ == '__main__':
    # Directory with the current .h5 files
    h5_path = "/gpfs/alpine/world-shared/stf011/junqi/smc/train/"
    # Directory we want to save new .h5 files to. Must end in /
    h5_save_path = ""
    # JSON file with the overall distribution in it
    distribution_JSON_path = "../distributions/dataframes/overall_distribution.json"

    # These are the .h5 files we want to create.
    # Final files will be at h5_save_path + "massaged" + fileNames + ".h5"
    fileNames = ["Train", "Dev", "Test"]
    # Rough ratio of sizes of the new .h5 files to be created.
    # In this case, Train will be about 5 times as large as Dev and Test
    fileRatios = [5, 1, 1]

    # Check if we have already made these files before.
    # If so, no need to remake them.
    firstPath = "{}massaged{}.h5".format(h5_save_path, fileNames[0])
    if os.path.exists(firstPath) and os.path.isfile(firstPath):
        print("Files already exist. Ending process.")
        return

    # Pull out overall distributions, as generated by datachallenge2/distributions/functions/find_all_distribution.py
    # This will be used to identify sparce space groups. Space groups with less than 30 entities will be copied
    # in their entirety to each of the new .h5 files created
    space_group_distribution = _convert_JSON_to_arr(distribution_JSON_path)

    # Create new .h5 files to fill out
    h5Files = _setup_h5_datasets(h5_save_path, fileNames, fileRatios)

    # Iterate through current .h5 files and move distribute the entries
    # into the newly created .h5 files
    curFilePaths = sorted([os.path.join(h5_path, aFileName) for aFileName in os.listdir(directory) if aFileName.endswith('.h5')])

    for aFilePath in curFilePaths:
        try:
            anH5File = h5py.File(aFilePath, 'r')
            _distribute_dataset(anH5File, h5Files, space_group_distribution)
            print("Distributed {} across new datasets".format(aFilePath))
            anH5File.close()
        except OSError:
            print("Could not read {}. Skipping".format(aFilePath))

    # Closes the newly created .h5 files
    for h5File in h5Files:
        h5File.close()

    print("Finished distribution of all datasets. Newly created datasets can be found in {}".format(h5_save_path))
