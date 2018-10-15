#!/usr/bin/python
from __future__ import with_statement
import sys
import glob
import os
import pandas as pd
import numpy as np
import zlib
from PIL import Image
import matplotlib.pyplot as plt

if len(sys.argv) > 1:
	PATH=str(sys.argv[1])
else:
	PATH='./'
 
files=glob.glob(PATH+'*.dat') 

for file in files:
	ndir, nfile  = os.path.split(file)
	ndir=ndir+'/'
	try:
		with open(file, mode='rb') as binary_file:
			data = binary_file.read() 
	except IOError as error:              
		print('oops! File '+nfile+' can not be read.')     
	if b'[Parameter]' in data:
		STMAFMVersion = 1
	elif b'[Paramet32]' in data:
		STMAFMVersion = 2
	elif b'[Paramco32]' in data:
		STMAFMVersion = 3
	else:
	# If none of these is found, stop and signal file error.
		print ('Createc DAT file version does not match')

	# Read out all header information until the max header byte of 16384 bytes.
	header_size=16384
	header_binary =data[0:header_size]

	idx = header_binary.index(b'DSP-COMPDATE')
	header_binary = header_binary[:idx] + b'\r' + header_binary[idx:];
	header_binary=header_binary.splitlines()
	ind = [i for i, s in enumerate(header_binary) if b'DSP-COMPDATE' in s][0]; header_binary[ind]


	d = []
	for i in range(1,ind):
		tmp=header_binary[i].split(b'=');
		d.append((tmp[0],tmp[1]))
	SplittedLine=pd.DataFrame(d, columns=('parameter', 'value'))

	Header={}
	Header['ScanPixels_X'] = int(SplittedLine.loc[SplittedLine['parameter'] == b'Num.X / Num.X'].value.item())
	Header['ScanPixels_Y'] = int(SplittedLine.loc[SplittedLine['parameter'] == b'Num.Y / Num.Y'].value.item())
	Header['GainX'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'GainX / GainX'].value.item())
	Header['GainY'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'GainY / GainY'].value.item())
	Header['GainZ'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'GainZ / GainZ'].value.item())
	Header['GainPreamplifier'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Gainpreamp / GainPre 10^'].value.item())
	Header['ChannelCount'] = int(SplittedLine.loc[SplittedLine['parameter'] == b'Channels / Channels'].value.item())
	Header['DACToZConversionFactor'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Dacto[A]z'].value.item())
	Header['DACToXYConversionFactor'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Dacto[A]xy'].value.item())
	Header['ScanRange_X'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Length x[A]'].value.item())
	Header['ScanRange_Y'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Length y[A]'].value.item())
	Header['ScanOffset_X'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Scanrotoffx / OffsetX'].value.item())
	Header['ScanOffset_Y'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Scanrotoffy / OffsetY'].value.item())
	Header['Bias'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Biasvolt[mV]'].value.item())
	Header['Current'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Current[A]'].value.item())
	Header['ACQ_Time'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Sec/Image:'].value.item())
	Header['ScanAngle'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Rotation / Rotation'].value.item())
	Header['ZControllerSetpoint'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'FBLogIset'].value.item())
	Header['ZControllerIntegralGain'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'FBIntegral'].value.item())
	Header['ZControllerProportionalGain'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'FBProp'].value.item())
	Header['PiezoX'] = float(SplittedLine.loc[SplittedLine['parameter'] == b'Xpiezoconst'].value.item())

	if STMAFMVersion == 1:
		BytePerPixel = 2
		# Header + 2 unused "NULL"-Bytes
		data_start=header_size+2
	elif STMAFMVersion == 2:
		BytePerPixel = 4
		# Header + 4 unused "NULL"-Bytes
		data_start=header_size+4
	elif STMAFMVersion == 3:
		BytePerPixel = 4
		data_start=header_size
		# No Seek of additional bytes, since they are compressed:
	image_data=data[data_start:]
	x = zlib.decompress(image_data)
	y = np.frombuffer(x, dtype=np.float32 ).transpose()
	y=y[1:]
	y=y[:-4*Header['ScanPixels_X']+1];
	#because some files have corrupted length we continue it with zeros to obtain coorect reshape to 2D	
	y_round_size=int(np.ceil(float(len(y))/float(Header['ScanPixels_X']))*Header['ScanPixels_X'])
	y_round=np.zeros(y_round_size);
	y_round[:len(y)]=y
	mat_image=y_round.reshape(-1,Header['ScanPixels_X']);
	y_size=Header['ScanPixels_Y']
	pic1=mat_image[:y_size,:]
	pic2=mat_image[y_size:2*y_size,:]
	pic3=mat_image[2*y_size:3*y_size,:]
	pic4=mat_image[3*y_size:,:] 
	# croping image from rows with zeros
	ind_list=np.where(~(pic1 == 0.0).all(axis=1))
	pic1_crop=pic1[ind_list[0],:]
	pic2_crop=pic2[ind_list[0],:] 
	pic3_crop=pic3[ind_list[0],:] 
	pic4_crop=pic4[ind_list[0],:]
	# inverting chanels with negative values
	if (np.sum(pic1_crop) < 0.0):
		pic1_crop=-pic1_crop
	if (np.sum(pic2_crop) < 0.0):
		pic2_crop=-pic2_crop
	if (np.sum(pic3_crop) < 0.0):
		pic3_crop=-pic3_crop
	if (np.sum(pic4_crop) < 0.0):
		pic4_crop=-pic4_crop    
	# making 3d array of 4 channels with crop images
	picture=np.dstack((pic1_crop, pic2_crop,pic3_crop,pic4_crop)) 

	output_dir=ndir+'npy_png/'
	if not os.path.exists(output_dir):
		os.makedirs(output_dir)
	file_npy=nfile[:-3]+'npy'
	file_png=nfile[:-3]+'png'
	np.save(output_dir+file_npy, picture)
	print(output_dir+file_npy)
	fig =plt.figure(figsize=(24, 4))
	columns = 4
	rows = 1
	fig.add_subplot(rows,columns ,1)
	plt.imshow(picture[:,:,0])
	plt.colorbar()
	fig.add_subplot(rows,columns ,2)
	plt.imshow(picture[:,:,1])
	plt.colorbar()
	fig.add_subplot(rows,columns ,3)
	plt.imshow(picture[:,:,2])
	plt.colorbar()
	fig.add_subplot(rows,columns ,4)
	plt.imshow(picture[:,:,3])
	plt.colorbar()	
	plt.savefig(output_dir+file_png)
	plt.close()
 


print('Processed '+str(len(files))+' files to a folder: '+output_dir+'.')

