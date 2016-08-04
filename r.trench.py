#!/usr/bin/env python

############################################################################
#
# MODULE:       r.trench
#
# AUTHOR(S):    Robert Kuszinger
#
# PURPOSE:      Creates a trapeziod profile trench on a raster dtm along a
#               vector line and calculates earthwork.
#
# COPYRIGHT:    (C) 2016 by GRASS development team
#
#               This program is free software under the GNU General
#               Public License (>=v2). Read the file COPYING that
#               comes with GRASS for details.
#
#############################################################################

#%module
#% description: Creates a trapeziod profile trench on a raster dtm along a vector line and calculates earthwork.
#% keyword: dtm
#% keyword: raster
#% keyword: trench
#% keyword: earthwork
#%end
#%option G_OPT_V_INPUT
#% key: linevector
#% multiple: no
#% description: Name of vector file with path. There should be only one line on the map.
#% required: YES
#% gisprompt: old,vector,vector
#% guisection: Input
#%end
#%option G_OPT_R_INPUT
#% key: dtm
#% multiple: no
#% gisprompt: old,cell,raster
#% description: DTM to process
#% guisection: Input
#%end
#%option
#% key: basename
#% type: string
#% description: Base name for output maps / files
#% required: YES
#% guisection: Output
#%end
#%option
#% key: startheight
#% required: YES
#% type: double
#% description: Start height of the first node of the vector line
#% guisection: Parameters
#%end
#%option
#% key: endheight
#% required: YES
#% type: double
#% description: Height of the last node of the vector line
#% guisection: Parameters
#%end
#%option
#% key: depth
#% answer: 7
#% required: YES
#% type: double
#% description: Depth of useful area / height of trapezoid / wet height in trench
#% guisection: Parameters
#%end
#%option
#% key: bottomwidth
#% type: double
#% answer: 10
#% required: YES
#% description: Bottom width of trapeziod
#% guisection: Parameters
#%end
#%option
#% key: maxwidth
#% answer: 50
#% required: YES
#% type: double
#% description: Top / max width of trapezoid (at depth height from bottom)
#% guisection: Parameters
#%end
#%option
#% key: sideratio
#% answer: 3
#% required: YES
#% type: double
#% description: Steps horizontally to raise 1 unit in height for the trapezoid slope
#% guisection: Parameters
#%end
#%option
#% key: vres
#% answer: 1
#% required: YES
#% type: double
#% description: Vertical resolution in calculation
#% guisection: Parameters
#%end
#%option
#% key: hres
#% type: double
#% answer: 10
#% required: YES
#% description: Horizontal resolution (both eastings and northings) in calculation
#% guisection: Parameters
#%end
#%option
#% key: dtmres
#% type: double
#% answer: 10
#% required: YES
#% description: Resolution in calculation when dealing with DTM
#% guisection: Parameters
#%end
#%option
#% key: pointdist
#% type: double
#% answer: 20
#% required: YES
#% description: Vector line / path is converted to series of points. This is their distance:
#% guisection: Parameters
#%end
#%option
#% key: limitrunlayers
#% type: integer
#% answer: 2000
#% required: YES
#% description: Maximum number of layers / slices in the calculation
#% guisection: Parameters
#%end





import sys
import os
import atexit
import re
#from subprocess import call
import tempfile

import grass.script as grass
from grass.exceptions import CalledModuleError
from grass.script.utils import try_rmdir
import copy

# initialize global vars
TMPFORMAT='BMP'
TMPLOC = None
SRCGISRC = None
GISDBASE = None
LAYERCOUNT = 10
# temp dir
REMOVETMPDIR = True
PROXIES = {}


def cleanup():
    
    # see end of main()
    grass.verbose(_("Module cleanup in: "+TMPDIR))
    os.system('rm '+ os.path.join( TMPDIR, '*'))
    if REMOVETMPDIR:
        try_rmdir(TMPDIR)
    else:
        grass.message("\n%s\n" % _("printws: Temp dir remove failed. Do it yourself, please:"))
        sys.stderr.write('%s\n' % TMPDIR % ' <---- this')



def render(astring,adic):
    grass.verbose(_("printws: Rendering into - BASE: " + LASTFILE))
    grass.verbose(_("printws: Rendering command: " + astring))
    
    dic = copy.deepcopy(adic)
    
    task = dic['task']
    del dic['task']
    # it should be replaced by grass.* API calls
    # os.system(astring)
    grass.run_command(task, "" , **dic)   #migration is going on
    

def ensureopt(option,value):
    if len(options[option])<1:
        return value
    else:
        return options[option]
    


#-----------------------------------------------------
#-----------------------------------------------------
#-----------------------------------------------------
#------------------- MAIN ---------------------------
#-----------------------------------------------------
#-----------------------------------------------------
#-----------------------------------------------------
#-----------------------------------------------------

def main():
    global GISDBASE


    #-------------------------------------------------
    #------- GETTING PARAMETERS ----------------------
    #------ because of smalltalk migration, variable names
    #------ with mixed capitals are kept
    
   
    hRes=float(ensureopt('hres',10))
    vRes=float(ensureopt('vres',1))
    pointDist=float(ensureopt('pointdist',20))
    endHeight=float(ensureopt('endheight',100))
    depth=float(ensureopt('depth',5))
    startHeight=float(ensureopt('startheight',1000))
    basedtm=ensureopt('dtm',"...")
    limitRunLayers=int(ensureopt('limitrunlayers',2000))
    chWidth=float(ensureopt('bottomwidth',100))
    chMaxWidth=float(ensureopt('maxwidth',300))
    # forced calculation
    sideRatio=float(chMaxWidth-chWidth)/2/depth
    reliefRes=float(ensureopt('dtmres',10))
    linevector=ensureopt('linevector','...') #mandatory so given for sure
    workPath=TMPDIR  # for os.path.join(,)
    # In smalltalk original startCover was the line vector name
    # it will be better this way (basename):
    
    if len(options['basename'])<1:
        startCover = linevector.split("@")[0]           # str(os.getpid())+"_r_trench_result"
    else:
        startCover = options['basename']
    

    #-------------------------------------------------
    #--------------END OF GETTING PARAMS--------------
    #-------------------------------------------------
    #-------------------------------------------------
    #-------------------------------------------------


    grass.run_command("g.region", vector=linevector, overwrite=True)
    grass.run_command("g.region",n="n+1000",w="w-1000",e="e+1000",s="s-1000", res=hRes, overwrite=True)
    grass.run_command("g.region",  save='l_work_' + startCover +'.region', overwrite=True)
    grass.run_command("v.to.points", input=linevector ,type="line", output='l_'+startCover+"_points", dmax=pointDist, overwrite=True)

    filename = os.path.join(workPath,startCover+".ascii")
    grass.run_command("v.out.ascii",input='l_'+startCover +"_points", layer=2, type="point", output=filename , columns="cat,lcat,along", format="point", overwrite=True)
    
    
    lines = []
    inFile = open(filename,'rU')
    for line in inFile.read().splitlines():
        lines.append(line.split("|"))
    inFile.close()
    
    length = float(lines[-1][4])
    
    grass.verbose("Path length: "+str(length))
    
    filename = os.path.join(workPath, startCover+'_'+'profileXY.csv')
    grass.verbose("Profile: "+str(filename))
    
    outFile = open(filename,"w")
    for each in lines:
        tmp = (each [0]) + ',' + (each [1])+ "\n"
        outFile.write(tmp)
    outFile.close()
    
    # next line should be more exact because with full trapeziod a wider area is necessary.
    # actually, we don't know at this point how big the deepest cut will be !!! ???
    #
    grass.run_command('v.buffer', overwrite=True, input=linevector, type="line", output='l_'+startCover+'_maxbuf', distance=str(float(chMaxWidth) / float(2)))
    grass.run_command('r.mask', overwrite=True, vector='l_'+startCover+'_maxbuf')
    grass.run_command('r.mapcalc', expression='l_'+startCover+'_maxbuf = '+basedtm,overwrite=True)
    
    
    s = grass.read_command('r.univar', overwrite=True, map='l_'+startCover+'_maxbuf')
    kv = grass.parse_key_val(s, sep=':')
    maxH = float(kv['maximum'])
    maxH = maxH+vRes
    grass.verbose("Maximum height: "+str(maxH))
    
    grass.run_command('r.mask', flags="r")
    
    vLevels = int(round(((maxH-endHeight)/vRes))) + 2
    grass.verbose("Number of levels: "+str(vLevels))

    hSeries = []
    
    # WINDOWS???
    os.system('rm '+os.path.join(workPath,'l_*.pascii'))
    
    db = {}
    
    for n in range(1,vLevels):
        hSeries.append(round ((n-1)*vRes+endHeight))
        db[n]= []
    
    quo = (endHeight-startHeight)/length
    
    grass.verbose("Start height: "+str(startHeight))
    grass.verbose("End height: "+str(endHeight))
    grass.verbose("Slope ratio (in meters / meter): "+str(quo))
    

    for aLine in lines:
        tmp = (quo*float(aLine[4]))+startHeight
        level = int(round(((tmp - endHeight)/vRes) + 1))
        layer = hSeries[level-1] # python arrays run from 0
        #print "---------------"+str(aLine)+"  level: "+str(level)
        db[level].append([aLine[0],aLine[1],aLine[2],chWidth/2])
        for levelUp in range(level+1,vLevels):
            bufferWidth = ((chWidth/2)+((levelUp - level)*vRes*sideRatio))
            if bufferWidth <= (chMaxWidth/2):
                db[levelUp].append([aLine[0],aLine[1],aLine[2],bufferWidth])

    for aKey in db:
        #print "---------------"+str(aKey)
        filename = os.path.join(workPath,'l_'+startCover+'_'+str(aKey).zfill(5)+'.pascii')
        outFile = open(filename,"w")
        for each in db[aKey]:
            tmp = str(each [0])+ '|' + str(each [1])+ '|' + str(each [2])+ '|' + str(each [3]) + "\n"
            outFile.write(tmp)
        outFile.close()

    grass.run_command('g.region', region='l_work_'+startCover+'.region')
    grass.run_command('g.region', res=str(hRes))

    #creating buffer for raster masking
    grass.run_command('v.buffer',overwrite=True, input=linevector, type='line', output='l_'+startCover+'_buf200', distance=200)
    grass.run_command('r.mask', overwrite=True, vector='l_'+startCover+'_buf200')

    for n in range(1,min(vLevels,limitRunLayers)):
        if len(db[n])>0:
            basename = 'l_'+startCover+'_'+str(n).zfill(5)
            grass.run_command('v.in.ascii', flags="n", overwrite=True, input=os.path.join(workPath,basename+'.pascii'), output=basename, columns="x double precision, y double precision, cat int, width double precision", cat=3)
            grass.run_command('v.buffer', flags="t", overwrite=True, input=basename, layer=1, type="point", output=basename+'_buf', column="width", tolerance=0.01)
            grass.run_command('v.db.addcolumn', map=basename+'_buf', col='level int')
            grass.run_command('v.db.update', map=basename+'_buf', column="level", value=str(hSeries[n-1]))
            grass.run_command('v.to.rast', overwrite=True, input=basename+'_buf', type="area", output=basename+'_buf_diss', use="attr", attribute_column="level")

    #CALCULATING FINAL RESULT

    grass.run_command('r.mask', flags='r')
    grass.run_command('g.region', region='l_work_'+startCover+'.region')
    grass.run_command('g.region', res=str(hRes))
    grass.run_command('r.mapcalc', expression='source = '+basedtm, overwrite=True)

    for n in range(1,min(vLevels,limitRunLayers)):
        if len(db[n])>0:
            basename = 'l_'+startCover+'_'+str(n).zfill(5)
            grass.verbose("Applying: "+basename)
            grass.run_command('r.mapcalc', expression='temp = if (isnull('+basename+'_buf_diss),source,if ( '+basename+'_buf_diss < source , '+basename+'_buf_diss, source))', overwrite=True)
            grass.run_command('g.rename', overwrite=True, raster='temp,source')
    grass.run_command('r.mapcalc', expression= 'dtm_'+startCover+' = if (isnull(source),'+basedtm+',source)', overwrite=True)
    grass.run_command('r.colors', map='dtm_'+startCover, color='bgyr')
    grass.run_command('g.region', res=str(reliefRes))
    grass.run_command('r.relief', overwrite=True, input='dtm_'+startCover,output='dtm_'+startCover+'_shaded', altitude=60, azimuth=45)


    grass.verbose("Calculating volume difference")

    grass.run_command('g.region', raster='dtm_'+startCover)
    grass.run_command('g.region', res=str(hRes))
    grass.run_command('r.mask', overwrite=True, vector='l_'+startCover+'_buf200')
    grass.run_command('r.mapcalc', overwrite=True, expression='diff_'+startCover+' = '+basedtm+' - dtm_'+startCover)

    s = grass.read_command('r.univar', overwrite=True, map='diff_'+startCover)
    kv = grass.parse_key_val(s, sep=':')
    sum = float(kv['sum'])

    grass.run_command('r.mask', flags="r")

    # WRITE LOG FILE

    filename = startCover+".txt"

    s = grass.read_command('g.region', flags="p3")
    kv = grass.parse_key_val(s, sep=':')

    xres = float(kv['nsres'])
    yres =  float(kv['ewres'])
    m3 = xres * yres * sum
    mt = m3 * 2.7 * 1000
    liebherr = mt / 350
    visontaev = mt / 1000 / 4200

    outFile = open(filename,"w")
    
    tmp=[]
    tmp.append("Path: "+linevector+" >> "+startCover+"\n")
    tmp.append("M3: "+str(m3)+"\n")
    tmp.append("Limestone tons: "+str(mt)+"\n")
    tmp.append("Kt limestone: "+str(mt/1000.0)+"\n")
    tmp.append("Liebherr T 282B: "+str(liebherr)+"\n")
    tmp.append("Visonta year "+str(visontaev)+"\n")
    
    for each in tmp:
        grass.message(each)
        outFile.write(each)
    
    outFile.close()

    grass.run_command('g.remove', flags="f", type="all", pattern='l_*'+startCover+'*')


    return 0

if __name__ == "__main__":
    options, flags = grass.parser()
    global TMPDIR
    TMPDIR = tempfile.mkdtemp()
    atexit.register(cleanup)
    sys.exit(main())
