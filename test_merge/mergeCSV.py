import pandas as pd
import glob
import os

all_files = glob.glob(os.getcwd() + "/*.csv")

li = []

for filename in all_files:
    df = pd.read_csv(filename, index_col=None, header=0)
    print(li)
    li.append(df)

frame = pd.concat(li, axis=0, ignore_index=True)

print(frame)