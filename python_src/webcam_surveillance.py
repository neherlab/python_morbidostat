#!/usr/bin/env python
import os
import argparse
import subprocess
import datetime
import time
import glob

parser = argparse.ArgumentParser(description="record the running morbidostat")
parser.add_argument('--dt', type=int, default = 600, help = 'number seconds between pictures')
parser.add_argument('--outdir', type=str, default='.', help = 'directory for output files')
params=parser.parse_args()

#cams = ['video1', 'video2']
dt = max(params.dt,15)  # seconds between pictures
outdir = params.outdir.rstrip('/')+'/'

# make directory if it does not exist
if not os.path.exists(outdir):
    os.mkdir(outdir)

pic_count = 0
while pic_count<10000: # loop forever (until 10000 pictures are taken)
    # make date string to label files
    now = datetime.datetime.now()
    now_str = now.strftime('%Y%m%d_%H-%M-%S')
    try:
        camlist = glob.glob('/dev/video*')
        camlist.remove('/dev/video0')
        for cam in camlist:
            camname = cam.replace('/dev/', '')
            args = ['-c', cam, '-s 640x480', '-o', outdir+camname+'_'+now_str+'.jpeg']
            print ' '.join(['streamer']+args)
            subprocess.call(['streamer']+args)
            time.sleep(10)  # allow 5 seconds for the picture taking
        time.sleep(params.dt-10*len(camlist)) # wait before taking next picture
        pic_count +=1 
    except:
        print now_str, "something went wrong."
        break
