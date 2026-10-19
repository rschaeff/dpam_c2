#!/usr/bin/python
import os, sys, string
from multiprocessing import Pool

def run_cmd(cmd):
	os.system(cmd)
	return cmd + " done"

pool = Pool(processes=int(sys.argv[2]))
fp = open(sys.argv[1],"r")
info = fp.readlines()
fp.close()
mylist = []
for line in info:
	mylist.append([line[:-1]])
	
result = []
for item in mylist:
	process = pool.apply_async(run_cmd,item)
	result.append(process)

for process in result:
	process.get()
