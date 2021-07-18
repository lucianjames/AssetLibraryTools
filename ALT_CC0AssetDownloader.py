import requests
import csv
import copy
import zipfile
import os
import re
import sys

def strToNoneType(x):
	if x == 'None':
		x = None
	return x

def strToBool(x):
	if x == 'True':
		return True
	if x == 'False':
		return False

def getFilename_fromCd(cd):
	if not cd:
		return None
	fname = re.findall('filename=(.+)', cd)
	if len(fname) == 0:
		return None
	return fname[0]

def filterByKeyword(assets, keyword):
	i = 0
	while i < len(assets):
		if keyword.upper() not in assets[i][0].upper():
			assets.pop(i)
		else:
			i+=1
	return assets

def filterByDownloadAttribute(assets, attribute):
	i = 0
	while i < len(assets):
		if assets[i][1] != attribute:
			assets.pop(i)
		else:
			i+=1
	return assets

def filterByFileExtension(assets, extension):
	i = 0
	while i < len(assets):
		if assets[i][2].upper() != extension.upper():
			assets.pop(i)
		else:
			i+=1
	return assets

def getAssetsByFilters(assets, assetfilters):
	assetsCopy = copy.deepcopy(assets) #deepcopy to avoid modifying original assets list
	if assetfilters[0] != None:
		assetsCopy = filterByKeyword(assetsCopy, assetfilters[0])
	if assetfilters[1] != None:
		assetsCopy = filterByDownloadAttribute(assetsCopy, assetfilters[1])
	if assetfilters[2] != None:
		assetsCopy = filterByFileExtension(assetsCopy, assetfilters[2])
	return assetsCopy

def download(assets):
	fileSize = 0
	for i in assets:
		fileSize += int(i[3])
	print("Attempting to download {0} assets with a filesize of {1} bytes ({2} gigabytes)".format(len(assets), fileSize, fileSize/1e+9))
	for i in assets:
		try:
			print("Downloading {0}_{1} from {2}".format(i[0], i[1], i[4]))
			url = i[5]
			r = requests.get(url, allow_redirects=True)
			open(saveLocation+i[0]+'_'+i[1]+'.'+i[2], 'wb').write(r.content)
			print(saveLocation+i[0]+'_'+i[1]+'.'+i[2])
		except Exception as e:
			print("Failed to download {0}_{1} from {2}".format(i[0], i[1], i[4]))
			print(e)

		if i[2] == "zip" and unZip == True:
			try:
				print("Unzipping {0}_{1}.{2}".format(i[0],i[1],i[2]))
				with zipfile.ZipFile(saveLocation+i[0]+'_'+i[1]+'.'+i[2], 'r') as zip_ref:
					zip_ref.extractall(saveLocation+i[0]+'_'+i[1])
				if deleteZips == True:
					os.remove(saveLocation+i[0]+'_'+i[1]+'.'+i[2])
			except Exception as e:
				print("Failed to unzip {0}_{1}.{2}".format(i[0], i[1], i[2]))
				print(e)




#AssetLibraryTools will do the input checking for this script, we just need to do some conversions
print(sys.argv)
saveLocation = sys.argv[1] + '/'
keywordFilter = strToNoneType(sys.argv[2])
attributeFilter = strToNoneType(sys.argv[3])
extensionFilter = strToNoneType(sys.argv[4])
unZip = strToBool(sys.argv[5])
deleteZips = strToBool(sys.argv[6])

headers = {'User-Agent' : 'LJ3DSCRIPT'}
url = 'https://ambientcg.com/api/v2/downloads_csv'
print("Downloading asset data from https://ambientcg.com/api/v2/downloads_csv\n")
r = requests.get(url, allow_redirects=True, headers=headers)
filename = getFilename_fromCd(r.headers.get('content-disposition'))
open(filename, 'wb').write(r.content)
#['assetId', 'downloadAttribute', 'filetype', 'size', 'downloadLink', 'rawLink']
with open(filename, newline='') as f:
	reader = csv.reader(f)
	assets = list(reader)
assets.pop(0)
listOfDownloadAttributes = []
listOfFileExtensions = []
totalSize = 0
for i in assets:
	if i[1] not in listOfDownloadAttributes:
		listOfDownloadAttributes.append(i[1])
	if i[2] not in listOfFileExtensions:
		listOfFileExtensions.append(i[2])
	totalSize += int(i[3])
print("Loaded csv file and found {0} assets\n".format(len(assets)))

filteredAssets = getAssetsByFilters(assets, [keywordFilter, attributeFilter, extensionFilter])
filteredAssets.sort()
filteredTotalSize = 0
for i in filteredAssets:
	filteredTotalSize += int(i[3])
print("=====\nFound {0} assets that match the filters, with a combined size of {1} bytes ({2} gigabytes)".format(len(filteredAssets), filteredTotalSize, filteredTotalSize/1e+9))
print("=====\nDisplay asset names? (y/n)")


while True:
	userInput = input()
	if userInput == 'y' or userInput == 'Y':
		for i in filteredAssets:
			print(i[0]+"_"+i[1])
		break
	if userInput == 'n' or userInput == 'N':
		break
	print("Invalid input")


print("=====\nWould you like to download these assets? (y/n)")
while True:
	userInput = input()
	if userInput == 'y' or userInput == 'Y':
		download(filteredAssets)
		break
	if userInput == 'n' or userInput == 'N':
		break
	print("Invalid input")
