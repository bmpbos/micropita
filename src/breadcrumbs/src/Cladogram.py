"""
Author: Timothy Tickle
Description: Class to call circlader and create dendrograms.
"""

#####################################################################################
#Copyright (C) <2012>
#
#Permission is hereby granted, free of charge, to any person obtaining a copy of
#this software and associated documentation files (the "Software"), to deal in the
#Software without restriction, including without limitation the rights to use, copy,
#modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
#and to permit persons to whom the Software is furnished to do so, subject to
#the following conditions:
#
#The above copyright notice and this permission notice shall be included in all copies
#or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#####################################################################################

__author__ = "Timothy Tickle"
__copyright__ = "Copyright 2012"
__credits__ = ["Timothy Tickle"]
__license__ = "MIT"
__maintainer__ = "Timothy Tickle"
__email__ = "ttickle@sph.harvard.edu"
__status__ = "Development"

#External libraries
from AbundanceTable import AbundanceTable
from CommandLine import CommandLine
from ConstantsBreadCrumbs import ConstantsBreadCrumbs
from ConstantsFiguresBreadCrumbs import ConstantsFiguresBreadCrumbs
import math
import numpy as np
import os
import re
import scipy.stats
from ValidateData import ValidateData
#import scipy.stats.stats as stats

class Cladogram:
  """
  This class manages creating files for Circlader and calling circulator.
  """

  #Script name
  circladerScript=None

  #Constants
  c_sTaxa="Taxa"
  c_sCircle="Circle"
  c_sBorder="Border"
  c_sShape="Shape"
  c_sAlpha="Alpha"
  c_sForced="Forced"

  #Numpy array (structured array) holding data
  #Should be SampleID, Sample Abundances/Data (samples = columns).....
  npaAbundance = None
  #List of sample names
  lsSampleNames = None
  #Name of output image
  strImageName = "Cladogram.png"
  #String used to call the sample id column
  strSampleID = "ID"
  strUnclassified = "unclassified"

  #Minimum size of clade (terminal node count for clade)
  iMinCladeSize = 1
  #Level of ancestry to filter at (starts with 0 and based on the input file)
  iCladeLevelToMeasure = 1
  iCladeLevelToReduce = 1
  cFeatureDelimiter = "|"

  #Flags
  #Turns on (True) or off (False) abundance-based filtering
  fAbundanceFilter = False
  #Turns on (True) or off (False) clade size-based filtering
  fCladeSizeFilter = False
  #Indicate if the following files were made
  fSizeFileMade=False
  fCircleFileMade=False
  fColorFileMade=False
  fTickFileMade=False
  fHighlightFileMade=False

  #Circlader files
  strTreeFilePath="_Taxa.txt"
  strCircleFilePath = "_Circle.txt"
  strColorFilePath="_Color.txt"
  strTickFilePath="_Tick.txt"
  strHighLightFilePath="_HighLight.txt"
  strSizeFilePath="_Size.txt"
  strStyleFilePath=""

  #Thresholds
  #Controls the showing of taxa
  c_dPercentileCutOff = 90.0
  c_dPercentageAbovePercentile = 1.0

  #Minimum average abundance score when using log scale
  c_dMinLogSize = 0.0000000001
  #Constant used to maginfy the size difference in the taxa (log only)
  c_dLogScale = 1000000
  #When after log10, an addition scaling adjustment (use this)
  c_dCircleScale = 3

  #Data for circular files
  #Used to change IDs to proper labels
  dictConvertIDs = None
  #Labels to be relabeled
  dictRelabels = None
  #Colors
  dictColors = None
  #Elements that are forced to be highlighted
  dictForcedHighLights = None
  #Ticks
  llsTicks = None
  #Forced root of the tree, discarding data as needed.
  strRoot = None
  #Holds circle data as a list of dictionaries
  #One dictionary per circle
  ldictCircleData = None

  def __init__(self):
    self.dictForcedHighLights = dict()

  #Happy Path Tested
  def addHighLights(self, dictClades,fOverwrite):
    """
    This methods allows highlighting to be added.
    When an element is added in this manner it will not be filtered out.
    These elements, if existing in the tree will be highlighted the named color given.
    This color name should be supplied in the set Color Data method
    {strName1:strColorName1,strName2:strColorName2,...}

    :param dictClades: Names of elements, if found in the tree which should be highlighted
    :type: dictClades Dictionary of element name (string) and element color (string) 
    :param fOverwrite: If element is already indicated to be highlighted, overwrite the color to the one provided here.
    :type: fOverwrite boolean (True == overwrite color)
    """
    if ValidateData.funcIsValidDictionary(dictClades):
        if ValidateData.funcIsValidBoolean(fOverwrite):
            for strElement in dictClades:
                if(strElement in self.dictForcedHighLights):
                    if(fOverwrite):
                        self.dictForcedHighLights[strElement] = dictClades[strElement]
                else:
                    self.dictForcedHighLights[strElement] = dictClades[strElement]

  #Not tested
  def getHighLights(self):
    return self.dictForcedHighLights

  #Not tested
  def forceRoot(self, strRoot):
    """
    This method allows one to root the tree at a certain level and value
    Only taxa that contain this value in their ancestry will be plotted
    The root will be the value given, any previous heirachy will be ignored
    This will remove highlighted data if indicated to do so

    :params strRoot: Where to root the tree
    :type: strRoot String
    """
    self.strRoot = strRoot

  def generate(self, strImageName, strStyleFile, sTaxaFileName, strCircladerScript = ConstantsBreadCrumbs.c_strCircladerScript, iTerminalCladeLevel = 10, sColorFileName=None, sTickFileName=None, sHighlightFileName=None, sSizeFileName=None, sCircleFileName=None):
    """
    This is the method to call to generate a cladogram using circlader.
    The default data file is an abundance table unless the getDa function is overwritten.

    :param strImageName: File name to save the output cladogram image
    :type: strImageName File name (string)
    :param strStyleFile: File path indicating the style file to use
    :type: strStyleFile File path (string)
    :param sTaxaFileName: File path indicating the taxa file to use
    :type: sTaxaFileName File path (string)
    :param strCircladerScript: File path to the Circlader script
    :type: String
    :param iTerminalCladeLevel: Clade level to use as terminal in plotting
    :type: iTerminalCladeLevel integer starting with 1
    :param strColorFile: File path indicating the color file to use
    :type: strColorFile File path (string)
    :param strTickFile: File path indicating the tick file to use
    :type: strTickFile File path (string)
    :param strHighlightFile: File path indicating the highlight file to use
    :type: strHighlightFile File path (string)
    :param strSizeFile: File path indicating the size file to use
    :type: strSizeFile File path (string)
    :param sCircleFileName: File path of circlader circle file.
    :type: String
    """

    if self.npaAbundance == None:
      print "Cladogram::generate. The data was not set so an image could not be generated"
      return False

    #Set script
    self.circladerScript = strCircladerScript

    #Set output file name
    self.strImageName = strImageName

    #Check files exist and remove files which will be written
    self.manageFilePaths(sTaxaFileName, strStyleFile, sColorFileName, sTickFileName, sHighlightFileName, sSizeFileName, sCircleFileName)

    #Get IDs
    lsIDs = [strId for strId in list(self.npaAbundance[self.strSampleID])]

    #Generate a dictionary to convert the ids to correct format
    #Fix unclassified names
    #Make numeric labels as indicated
    self.dictConvertIDs = self.generateLabels(lsIDs)

    #Remove taxa lower than the display clade level
    lsCladeAndAboveFeatures = []
    for sFeature in lsIDs:
        if len(sFeature.split(self.cFeatureDelimiter)) <= iTerminalCladeLevel:
            lsCladeAndAboveFeatures.append(sFeature)
    lsIDs = lsCladeAndAboveFeatures

    #Filter by abundance
    if(self.fAbundanceFilter):
      lsIDs = self.filterByAbundance(lsIDs)

    #Update to the correct root
    lsIDs = self.updateToRoot(lsIDs)

    #Set highlights to root for consistency
    if(not self.strRoot == None):
      dictRootedHighLights = dict()
      if not self.dictForcedHighLights == None:
        for sKey in self.dictForcedHighLights.keys():
          strUpdatedKey = self.updateToRoot([sKey])
          dictRootedHighLights[strUpdatedKey[0]]=self.dictForcedHighLights[sKey]
        self.dictForcedHighLights = dictRootedHighLights

    #Set relabels to root for consistency
    if(not self.strRoot == None):
      dictRootedLabels = dict()
      if not self.dictRelabels == None:
        for sKey in self.dictRelabels.keys():
          strUpdatedKey = self.updateToRoot([sKey])
          dictRootedLabels[strUpdatedKey[0]]=self.dictRelabels[sKey]
        self.dictRelabels = dictRootedLabels

    #Filter by clade size Should be the last filter.
    #It is not a strong filter but cleans up images
    if(self.fCladeSizeFilter):
      lsIDs = self.filterByCladeSize(lsIDs)

    #Add in forced highlighting
    lsIDs.extend(self.dictForcedHighLights.keys())
    lsIDs = list(set(lsIDs))

    #Add in forced circle data
    for dictCircleData in self.ldictCircleData:
      if(dictCircleData[self.c_sForced]):
        lsTaxa = dictCircleData[self.c_sTaxa]
        lsAlpha = dictCircleData[self.c_sAlpha]
        lsAddTaxa = []
        [lsAddTaxa.append(lsTaxa[tpleAlpha[0]]) if not tpleAlpha[1] == '0.0' else 0 for tpleAlpha in enumerate(lsAlpha)]
        lsIDs.extend(lsAddTaxa)
    lsIDs = list(set(lsIDs))

    #Create circle files (needs to be after any filtering because it has a forcing option).
    if not self.createCircleFile(lsIDs):
      return False

    #Generate / Write Tree file
    if not self.createTreeFile(lsIDs):
      return False

    #Generate / Write Highlight file
    if not self.createHighlightFile(lsIDs):
      return False

    #Generate / write color file
    if(self.dictColors is not None):
        lsColorData = [ConstantsBreadCrumbs.c_cTab.join([sColorKey,self.dictColors[sColorKey]]) for sColorKey in self.dictColors]
        self.writeToFile(self.strColorFilePath, ConstantsBreadCrumbs.c_strEndline.join(lsColorData), False)
        self.fColorFileMade=True

    #Generate / write tick file
    if(self.llsTicks is not None):
        lsTickData = [ConstantsBreadCrumbs.c_cTab.join(lsTicks) for lsTicks in self.llsTicks]
        self.writeToFile(self.strTickFilePath, ConstantsBreadCrumbs.c_strEndline.join(lsTickData), False)
        self.fTickFileMade=True

    #Generate / Write size data
    if not self.createSizeFile(lsIDs):
      return False

    #Call commandline
    lsCommand = [self.circladerScript, self.strTreeFilePath, self.strImageName, "--style_file", self.strStyleFilePath, "--tree_format", "tabular"]
    if(self.fSizeFileMade):
      lsCommand.extend(["--size_file", self.strSizeFilePath])
    if(self.fColorFileMade):
      lsCommand.extend(["--color_file", self.strColorFilePath])
    if(self.fTickFileMade):
      lsCommand.extend(["--tick_file", self.strTickFilePath])
    if(self.fHighlightFileMade):
      lsCommand.extend(["--highlight_file", self.strHighLightFilePath])
    if(self.fCircleFileMade):
      lsCommand.extend(["--circle_file", self.strCircleFilePath])
    CommandLine().runCommandLine(lsCommand)

  #Happy path tested
  def setColorData(self, dictColors):
    """
    This methods allows color information to be specified.
    Need to give a dictionary having a name (key)(string) and color (value)(string RGB)data
    {strName1:Color,strName2:Color...}
    Name will be a string name that references what needs to be this color
    Color data should be a string in the RGB format 0-255,0-255,0-255

    :param dictColors: Color Name and RGB specification
    :type: dictColorsDictionary strings 
    """
    if ValidateData.funcIsValidDictionary(dictColors):
      self.dictColors = dictColors
      if not ConstantsFiguresBreadCrumbs.c_strBackgroundColorName in self.dictColors:
        self.dictColors[ConstantsFiguresBreadCrumbs.c_strBackgroundColorName]=ConstantsFiguresBreadCrumbs.c_strBackgroundColor

  #Not tested
  def setAbundanceData(self, abtbAbundanceTable):
    """
    Sets the abundance data the Cladogram will use to plot

    :params abtAbundanceTable: AbundanceTable to set
    :type: AbundanceTable
    """
    self.npaAbundance = abtbAbundanceTable.funcGetAbundanceCopy()
    self.strSampleID = abtbAbundanceTable.funcGetIDMetadataName()
    self.lsSampleNames = abtbAbundanceTable.funcGetSampleNames()

  #Not tested
  def setFilterByAbundance(self, fAbundanceFilter, dPercentileCutOff = 90.0,  dPercentageAbovePercentile = 1.0):
    """
    Switch filtering by abundance on and off.
    fAbundanceFilter == True indicates filtering is on

    :param fAbundanceFilter: Switch to turn on (true) and off (false) abundance-based filtering
    :type: fAbundanceFilter boolean
    :param dPercentileCutOff: Percentage between 100.0 to 0.0.
    :type: double
    :param dPercentageAbovePercentile: Percentage between 100.0 to 1.0.
    :type: double
    """
    self.fAbundanceFilter = fAbundanceFilter
    self.c_dPercentileCutOff = dPercentileCutOff
    self.c_dPercentageAbovePercentile = dPercentageAbovePercentile

  #Not Tested
  def setCircleScale(self, iScale):
    """
    Is a scale used to increase or decrease node sizes in the the cladogram to make more visible
    iScale default is 3

    :param iScale: Integer to increase the relative sizes of nodes
    :type: iScale integer
    """
    self.c_dCircleScale = iScale

  #Not tested
  def setFeatureDelimiter(self, cDelimiter):
    """
    Set the delimiter used to parse the consensus lineages of features.

    :param cDelimiter: The delimiter used to parse the consensus lineage of features.
    :type: Character
    """
    if cDelimiter:
      self.cFeatureDelimiter = cDelimiter

  #Not tested
  def setFilterByCladeSize(self, fCladeSizeFilter, iCladeLevelToMeasure = 3, iCladeLevelToReduce = 1, iMinimumCladeSize = 5, cFeatureDelimiter = None, strUnclassified="unclassified"):
    """
    Switch filtering by clade size on and off.
    fCladeSizeFilter == True indicates filtering is on
    NOT 0 based.

    :param fCladeSizeFilter: Switch to turn on (true) and off (false) clade size-based filtering
    :type: fCladeSizeFilter boolean
    :param iCladeLevelToMeasure: The level of the concensus lineage that is measure or counted. Should be greater than iCladeLevelToReduce (Root is 1)
    :type: iCladeLevelToMeasure int
    :param iCladeLevelToReduce: The level of the concensus lineage that is reduced if the measured level are not the correct count (Root is 1)
    :type: iCladeLevelToReduce int
    :param iMinimumCladeSize: Minimum count of the measured clade for the clade to be kept
    :type: iMinimumCladeSize int
    :param cFeatureDelimiter: One may set the feature delimiter if needed.
    :type: Character
    :param strUnclassified: String indicating unclassifed features
    :type: String
    """
    self.fCladeSizeFilter = fCladeSizeFilter
    if iCladeLevelToMeasure > 0:
        self.iCladeLevelToMeasure = iCladeLevelToMeasure
    if iCladeLevelToReduce > 0:
        self.iCladeLevelToReduce = iCladeLevelToReduce
    if iMinimumCladeSize > 0:
        self.iMinCladeSize = iMinimumCladeSize
    if cFeatureDelimiter:
        self.cFeatureDelimiter = cFeatureDelimiter
    if strUnclassified:
        self.strUnclassified = strUnclassified

  #Not tested
  def setTicks(self, llsTicks):
    """
    This methods allows tick information to be specified.
    Need to generate a list of lists each having a tick level (number starting at 0 as a string), and tick name
    #Lowest numbers are closest to the center of the tree
    [[#,Name1],[#,Name2]...]

    :param llsTicks: Level # and Name of level
    :type: llsTicks List of lists of strings 
    """
    self.llsTicks = llsTicks

  #Happy Path tested with createCircleFile
  def addCircle(self, lsTaxa, strCircle, dBorder=0.0, strShape="R", dAlpha=1.0, fForced=False):
    """
    This methods allows one to add a circle to the outside of the cladogram.

    :param lsTaxa: Taxa to highlight with this circle
    :type: lsTaxa List of strings (taxa names)
    :param strCircle: Circle the elements will be in, indicates color and circle level.
    :type: strCircle String circle 
    :param dBorder: Border size for the circle element border (between 0.0 and 1.0)
      can also be a list of dBorders.  If list, position must match lsTaxa.
    :type: dBorder Float of border size (or list of floats).
    :param strShape: String Indicator of shape or method to determine shape.
      Can also be a list of shapes.  If list, position must match lsTaxa.
    :type: strShape String to indicate the shape (may also be a list of strings).
        Default value is square.
        Valid shapes are R(Square), v(inward pointing triangle), ^(outward pointing triangle)
    :param dAlpha: The transparency of the circle element (between 0.0[clear] and 1.0[solid]).
      Can also be a list of floats.  If list, position must match lsTaxa.
    :type: dAlpha Float to indicate the transparency of the shape (may also be a list of strings).
    :param fForced: Forces item in the features in the circle to be displayed in the cladogram no matter thier passing filters.
    :type: Boolean
    """
    if(self.ldictCircleData == None):
      self.ldictCircleData = list()
    dictCircleData = dict()
    dictCircleData[self.c_sTaxa]=lsTaxa
    dictCircleData[self.c_sCircle]=strCircle
    dictCircleData[self.c_sBorder]=dBorder
    dictCircleData[self.c_sShape]=strShape
    dictCircleData[self.c_sAlpha]=dAlpha
    dictCircleData[self.c_sForced]=fForced

    self.ldictCircleData.append(dictCircleData)
    return True

  #Happy Path tested with AddCircle
  def createCircleFile(self, lsIDs):
    """
    Write circle data to file.

    :param lsIDs: Ids to include in the circle file
    :type: lsIDs List of strings
    """
    #If there is circle data
    if(not self.ldictCircleData == None):
      if self.strCircleFilePath == None:
        print("Error, there is no circle file specified to write to.")
        return False
      #Holds circle data {Taxaname:string updates correctly for output to file}
      dictCircleDataMethods = dict()
      lsCircleData = list()

      for dictCircleData in self.ldictCircleData:
        lsTaxa = dictCircleData[self.c_sTaxa]
        #Shape/s for taxa
        datShape = dictCircleData[self.c_sShape]
        fShapeIsList = (str(type(datShape)) == "<type 'list'>")
        #Border/s for taxa
        datBorder = dictCircleData[self.c_sBorder]
        fBorderIsList = (str(type(datBorder)) == "<type 'list'>")
        #Alpha/s for taxa
        datAlpha = dictCircleData[self.c_sAlpha]
        fAlphaIsList = (str(type(datAlpha)) == "<type 'list'>")
        #Circle name
        sCircleMethod = dictCircleData[self.c_sCircle]

        #Check to make sure the lengths of the array match up
        if(fShapeIsList):
          if not len(datShape) == len(lsTaxa):
            print("".join(["Error, Shapes were given as an list not of the size of the taxa list. Shape list length: ",str(len(datShape)),". Taxa list length: ",str(len(lsTaxa)),"."]))
            return False
        if(fBorderIsList):
          if not len(datBorder) == len(lsTaxa):
            print("".join(["Error, Border sizes were given as an list not of the size of the taxa list. Border list length: ",str(len(datBorder)),". Taxa list length: ",str(len(lsTaxa)),"."]))
            return False
        if(fAlphaIsList):
          if not len(datAlpha) == len(lsTaxa):
            print("".join(["Error, Alpha sizes were given as an list not of the size of the taxa list. Alpha list length: ",str(len(datAlpha)),". Taxa list length: ",str(len(lsTaxa)),"."]))
            return False

        #Update taxa to root if needed
        #When doing this if any of the other data is an array we have to edit them
        #as the taxa are edited for updating root
        if((not fShapeIsList) and (not fBorderIsList) and (not fAlphaIsList)):
          lsTaxa = self.updateToRoot(dictCircleData[self.c_sTaxa])
        else:
          #Initilize as lists or as the string value they already are
          lsUpdatedTaxa = list()
          datUpdatedShapes=list()
          if(not fShapeIsList):
            datUpdatedShapes = datShape
          datUpdatedBorders=list()
          if(not fBorderIsList):
            datUpdatedBorders = datBorder
          datUpdatedAlphas=list()
          if(not fAlphaIsList):
            datUpdatedAlphas = datAlpha

          #If a taxa is kept, keep associated list information
          #If not a list data, leave alone, it will be used globally for all taxa.
          iTaxaIndex = -1
          for sTaxa in lsTaxa:
            iTaxaIndex = iTaxaIndex + 1
            sUpdatedTaxa=self.updateToRoot([sTaxa])

            if len(sUpdatedTaxa)==1:
              lsUpdatedTaxa.append(sUpdatedTaxa[0])
              if(fShapeIsList):
                datUpdatedShapes.append(datShape[iTaxaIndex])
              if(fBorderIsList):
                datUpdatedBorders.append(datBorder[iTaxaIndex])
              if(fAlphaIsList):
                datUpdatedAlphas.append(datAlpha[iTaxaIndex])

          #Reset data to rooted data
          lsTaxa=lsUpdatedTaxa
          datShape=datUpdatedShapes
          datBorder=datUpdatedBorders
          datAlpha=datUpdatedAlphas

        #QC passes so we will add the circle to the figure and the ticks.
        #If there are ticks and if the circle is not already in the ticks.
        if(not self.llsTicks == None):
          strCircleName = dictCircleData[self.c_sCircle]
          fFound = False
          iHighestNumber = -1
          for tick in self.llsTicks:
            #Look for name
            if tick[1] == strCircleName:
              fFound = True
            #Find highest count
            if int(tick[0]) > iHighestNumber:
              iHighestNumber = int(tick[0])
          if not fFound:
            self.llsTicks.append([str(iHighestNumber+1),strCircleName])

        #If the circle is forced, add the taxa to the lsIDs
        #Otherwise we will only plot those that are matching 
        #the lsIDs and the circle taxa list.
        if dictCircleData[self.c_sForced]:
          for iAlpha in xrange(0,len(datAlpha)):
            if(not datAlpha[iAlpha] == "0.0"):
              lsIDs.append(lsTaxa[iAlpha])
          lsIDs = list(set(lsIDs))

        #For all taxa in the cladogram
        for sTaxa in lsTaxa:
          #Store circle content name in dictionary
          if not sTaxa in dictCircleDataMethods:
            #Reset name to . delimited
            asNameElements = filter(None,re.split("\|",sTaxa))

            sCurTaxaName = asNameElements[len(asNameElements)-1]
            if(len(asNameElements)>1):
              if(sCurTaxaName=="unclassified"):
                sCurTaxaName = ".".join([asNameElements[len(asNameElements)-2],sCurTaxaName])
            sCurTaxa = ".".join(asNameElements)
            #Add to dictionary
            dictCircleDataMethods[sTaxa] = sCurTaxa

          #If the taxa is in the selected method
          if sTaxa in lsTaxa:
            #Index of the id in the circle data
            iTaxaIndex = lsTaxa.index(sTaxa)
            #Get border
            sBorder = ""
            if(fBorderIsList):
              sBorder = str(datBorder[iTaxaIndex])
            else:
              sBorder = str(datBorder)
            #Get shape
            sShape = ""
            if(fShapeIsList):
              sShape = datShape[iTaxaIndex]
            else:
              sShape = datShape
            #Get alpha
            sAlpha = ""
            if(fAlphaIsList):
              sAlpha = str(datAlpha[iTaxaIndex])
            else:
              sAlpha = str(datAlpha)
            dictCircleDataMethods[sTaxa]=dictCircleDataMethods[sTaxa]+"".join([ConstantsBreadCrumbs.c_cTab,sCircleMethod,":",sAlpha,"!",sShape,"#",sBorder])
          else:
            dictCircleDataMethods[sTaxa]=dictCircleDataMethods[sTaxa]+"".join([ConstantsBreadCrumbs.c_cTab,sCircleMethod,":0.0!R#0.0"])

      if len(dictCircleDataMethods)>0:
        lsTaxaKeys = dictCircleDataMethods.keys()
        sCircleContent = dictCircleDataMethods[lsTaxaKeys[0]]
        for sTaxaKey in lsTaxaKeys[1:len(lsTaxaKeys)]:
          sCircleContent = ConstantsBreadCrumbs.c_strEndline.join([sCircleContent,dictCircleDataMethods[sTaxaKey]])
        self.writeToFile(self.strCircleFilePath, sCircleContent, False)
        self.fCircleFileMade=True

        return True
    self.fCircleFileMade=False
    return False

  #Happy Path tested
  def createHighlightFile(self, lsIDs):
    """
    Write highlight data to file

    :param lsIDs: Ids to include in the highlight file
    :type: lsIDs List of strings
    """
    lsHighLightData = list()
    #Each taxa name
    for sID in lsIDs:
      sCurColor = ""
      #Rename taxa to be consisten with the . delimit format
      asNameElements = filter(None,re.split("\|",sID))
      sCurTaxaName = asNameElements[len(asNameElements)-1]
      if(len(asNameElements)>1):
        if(sCurTaxaName=="unclassified"):
          sCurTaxaName = ".".join([asNameElements[len(asNameElements)-2],sCurTaxaName])
      sCurTaxa = ".".join(asNameElements)

      sCurLabel = ""
      #Get color
      sColorKey = ""
      if(sID in self.dictForcedHighLights):
        sColorKey = self.dictForcedHighLights[sID]
        if(sColorKey in self.dictColors):
          sCurColor = self.formatRGB(self.dictColors[sColorKey])
        #Get label
        if(self.dictRelabels is not None):
          if(sID in self.dictRelabels):
            sCurLabel = self.dictRelabels[sID]
        if(sCurLabel == ""):
          lsHighLightData.append(ConstantsBreadCrumbs.c_cTab.join([sCurTaxa,sCurTaxaName,sCurLabel,sCurColor]))
        else:
          lsHighLightData.append(ConstantsBreadCrumbs.c_cTab.join([sCurTaxa,sCurLabel,sCurLabel,sCurColor]))

    if len(lsHighLightData)>0:
      self.writeToFile(self.strHighLightFilePath, ConstantsBreadCrumbs.c_strEndline.join(lsHighLightData), False)
      self.fHighlightFileMade=True
    return True

  #Happy path tested
  def createSizeFile(self, lsIDs):
    """
    Write size data to file

    :param lsIDs: Ids to include in the size file
    :type: lsIDs List of strings
    """
    if self.npaAbundance is not None:
      dMinimumValue = (self.c_dMinLogSize*self.c_dLogScale)+1
      lsWriteData = list()
      for rowData in self.npaAbundance:
        strCurrentId = rowData[0]
        #Reset to root if needed to match current data
        if(not self.strRoot == None):
          strCurrentId = self.updateToRoot([strCurrentId])
          if(len(strCurrentId) > 0):
            strCurrentId = strCurrentId[0]
        if(strCurrentId in lsIDs):
          dAverage = np.average(list(rowData)[1:])
          dSize = max([dMinimumValue,(dAverage*self.c_dLogScale)+1])
          lsWriteData.append(".".join(re.split("\|",strCurrentId))+ConstantsBreadCrumbs.c_cTab+str(math.log10(dSize)*self.c_dCircleScale))
      if len(lsWriteData)>0:
        self.writeToFile(self.strSizeFilePath, ConstantsBreadCrumbs.c_strEndline.join(lsWriteData), False)
        self.fSizeFileMade=True
    return True

  #Happy path tested 1
  def createTreeFile(self, lsIDs):
    """
    Write tree data to file. The tree file defines the internal cladogram and all it's points.

    :param lsIDs: Ids to include in the tree file as well as their ancestors
    :type: lsIDs List of strings
    """
    lsFullTree = list()
    for sID in lsIDs:
      lsIDElements = filter(None,re.split("\|",sID))
      sElementCur = lsIDElements[0]
      if(not sElementCur in lsFullTree):
        lsFullTree.append(sElementCur)
      if(len(lsIDElements) > 1):
        sNodePath = ""
        for iEndLevel in xrange(1,len(lsIDElements)+1):
          sCurAncestry = lsIDElements[0:iEndLevel]
          sNodePath = ".".join(sCurAncestry)
          if(not sNodePath in lsFullTree):
            lsFullTree.append(sNodePath)

    if len(lsFullTree)>0:
      self.writeToFile(self.strTreeFilePath, ConstantsBreadCrumbs.c_strEndline.join(lsFullTree), False)
    return True

  #Happy Path tested
  def filterByAbundance(self, lsIDs):
    """
    Filter by abundance. Specifically this version requires elements of
    the tree to have a certain percentage of a certain percentile in samples.

    :param lsIDs: Ids to filter
    :type: lsIDs List of strings
    """
    #list of ids to return that survived the filtering
    retls = list()
    if not self.npaAbundance is None:
      #Hold the cuttoff score (threshold) for the percentile of interest {SampleName(string):score(double)}
      dictPercentiles = dict()
      for index in xrange(1,len(self.npaAbundance.dtype.names)):
        dScore = scipy.stats.scoreatpercentile(self.npaAbundance[self.npaAbundance.dtype.names[index]],self.c_dPercentileCutOff)
        dictPercentiles[self.npaAbundance.dtype.names[index]] = dScore

      #Sample count (Ignore sample id [position 0] which is not a name)
      dSampleCount = float(len(self.npaAbundance.dtype.names[1:]))

      #Check each taxa
      for rowTaxaData in self.npaAbundance:
        sCurTaxaName = rowTaxaData[0]
        #Only look at the IDs given
        if(sCurTaxaName in lsIDs):
          dCountAbovePercentile = 0.0
          ldAbundanceMeasures = list(rowTaxaData)[1:]
          #Check to see if the abundance score meets the threshold and count if it does
          for iScoreIndex in xrange(0,len(ldAbundanceMeasures)):
            if(ldAbundanceMeasures[iScoreIndex] >= dictPercentiles[self.lsSampleNames[iScoreIndex]]):
              dCountAbovePercentile = dCountAbovePercentile + 1.0
          dPercentOverPercentile = dCountAbovePercentile / dSampleCount
          if(dPercentOverPercentile >= (self.c_dPercentageAbovePercentile/100.0)):
            retls.append(sCurTaxaName)
    return retls

  #Happy Path Tested
  def filterByCladeSize(self, lsIDs):
    """
    Filter by the count of individuals in the clade.

    :param lsIDs: Ids to filter
    :type: lsIDs List of strings
    """
    #First get terminal nodes
    lsTerminalNodes = AbundanceTable.funcGetTerminalNodesFromList(lsIDs,self.cFeatureDelimiter)

    #Count up clades
    cladeCounts = dict()
    
    #For each terminal node count the
    #Clades at clade levels
    for sTerminalNode in lsTerminalNodes:
        lsLineage = sTerminalNode.split(self.cFeatureDelimiter)
        iLineageCount = len(lsLineage)
        #If the lineage is shorter than the reduced clade level then no need to filter it
        if iLineageCount >= self.iCladeLevelToReduce:
            #If the lineage is longer than the reduced clade level and measuring clade level then count
            #or If the lineage is longer than the reduced clade level but shorter than the measuring clade,
            #only count if the last element is unclassified
            if (iLineageCount >= self.iCladeLevelToMeasure) or (lsLineage[-1] == self.strUnclassified):
                sLineage = self.cFeatureDelimiter.join(lsLineage[0:self.iCladeLevelToReduce])
                cladeCounts[sLineage] = cladeCounts.get(sLineage,0) + 1

    #Go through the IDs and reduce as needed using the clade counts
    retls = list()
    for sID in lsIDs:
        lsID = sID.split(self.cFeatureDelimiter)
        iIDCount = len(lsID)

        #Too short to filter
        if iLineageCount < self.iCladeLevelToReduce:
            retls.append(sID)
        #Check to see if the clade which is being reduced made the cut
        if iIDCount >= self.iCladeLevelToReduce:
            if (iIDCount >= self.iCladeLevelToMeasure) or (lsID[-1] == self.strUnclassified):
                if cladeCounts[self.cFeatureDelimiter.join(lsID[0:self.iCladeLevelToReduce])] >= self.iMinCladeSize:
                    retls.append(sID)

    return retls

  #Happy path tested
  def formatRGB(self, sColor):
    """
    Takes a string that is of the format 0-255,0-255,0-255 and converts it to the 
    color format of circlader _c_[0-1,0-1,0-1]

    :param sColor: String RGB format
    :type: sColor String
    """
    sCircladerColor = "_c_[1,1,1]"
    if(sColor is not None):
      sColorElements = filter(None,re.split(",",sColor))
      if(len(sColorElements)==3):
        iR = int(sColorElements[0])/255.0
        iG = int(sColorElements[1])/255.0
        iB = int(sColorElements[2])/255.0
        sCircladerColor = "".join(["_c_[",str(iR),",",str(iG),",",str(iB),"]"])
    return sCircladerColor

  #Happy path tested
  def generateLabels(self, lsIDs):
    """
    Labels for visualization. 
    Changes unclassified to one_level_higher.unclassified and enables numeric labeling / relabeling.
    Will only rename, will not add the label. The key must exist for the value to be used in replacing.

    :param lsIDs: Ids to include in the labels file
    :type: lsIDs List of strings
    """
    dictRet = dict()
    for sID in lsIDs:
        lsIDElements = filter(None,re.split("\|",sID))
        iIDElementsCount = len(lsIDElements)
        sLabel = lsIDElements[iIDElementsCount-1]
        #Fix unclassified
        if((sLabel == "unclassified") and (iIDElementsCount > 1)):
            sLabel = ".".join([lsIDElements[iIDElementsCount-2],sLabel])
        #Change to relabels if given
        if(self.dictRelabels is not None):
            if(sLabel in self.dictRelabels):
                sLabel = self.dictRelabels[sLabel]
        #Store lable
        dictRet[sID] = sLabel
    return dictRet

  #Happy path tested
  def manageFilePaths(self, sTaxaFileName, strStyleFile, sColorFileName=None, sTickFileName=None, sHighlightFileName=None, sSizeFileName=None, sCircleFileName=None):
    """
    This method sets the naming to the files generated that Circlader acts on.
    These files include the tree, color, highlight, tick, circle, and size files.
    Checks to make sure the file path to the syle file provided is an existing file.
    Deletes any existing files with these generated names (except for the style files).

    :param sStyleFile: File path indicating the style file to use
    :type: String
    :param strTaxaFile: File path indicating the taxa file to use
    :type: String
    :param sColorFile: File path indicating the color file to use
    :type: String
    :param sTickFile: File path indicating the tick file to use
    :type: String
    :param sHighlightFile: File path indicating the highlight file to use
    :type: String
    :param sSizeFile: File path indicating the size file to use
    :type: String
    :param sCircleFileName: File path for circle files
    :type: String
    :return boolean: True indicates success, false indicates error
    """
    #Do not remove the style file, it is static
    if strStyleFile is None:
      print("Error, style file is None")
      return(False)
    if not os.path.exists(strStyleFile):
      print("Error, no style file found.")
      return(False)
    else:
      self.strStyleFilePath = strStyleFile

    #Set output files and remove if needed
    self.strTreeFilePath = sTaxaFileName
    self.strColorFilePath = sColorFileName
    self.strTickFilePath = sTickFileName
    self.strHighLightFilePath = sHighlightFileName
    self.strSizeFilePath = sSizeFileName
    self.strCircleFilePath = sCircleFileName
    for sFile in [self.strTreeFilePath,self.strColorFilePath,self.strTickFilePath,
                  self.strHighLightFilePath,self.strSizeFilePath,self.strCircleFilePath]:
      if not sFile is None:
        if(os.path.exists(sFile)):
          os.remove(sFile)
    return True

  #Not tested
  def relabelIDs(self, dictLabels):
    """
    Allows the relabeling of ids. Can be used to make numeric labeling of ids or renaming

    :param dictLabels: Should label (key) (after unclassified is modified) and new label (value)
    :type: dictLabels Dictionary of string (key:label to replace) string (value:new label to use in replacing)
    """
    self.dictRelabels = dictLabels

  #Happy path tested
  def updateToRoot(self, lsIDs):
    """
    Updates the clade to the root given. The clade must contain the root and the level of the 
    root in the clade will be rest to it's first level, ignoring the previous levels of the clade.

    :param lsIDs: List of Clades that will be reset to the root specified by setRoot
    :type: lsIDs List of strings. Each string representing a clade.
    """

    if(self.strRoot is None):
      return lsIDs
    #Force root tree if indicated to do so
    lsRootedIDs = list()
    for sID in lsIDs:
      sIDElements = filter(None,re.split("\|",sID))
      if(self.strRoot in sIDElements):
        iRootIndex = sIDElements.index(self.strRoot)
        #If multiple levels of the clade exist after the new root merge them.
        if(len(sIDElements)>iRootIndex+2):
          lsRootedIDs.append("|".join(sIDElements[iRootIndex+1:]))
        #If only one level of the clade exists after the new root, return it.
        elif(len(sIDElements)>iRootIndex+1):
          lsRootedIDs.append(sIDElements[iRootIndex+1])
    return(lsRootedIDs)

  #Testing: Used extensively in other tests
  def writeToFile(self, strFileName, strDataToWrite, fAppend):
    """
    Helper function that writes a string to a file

    :param strFileName: File to write to
    :type: strFileName File path (string)
    :param strDataToWrite: Data to write to file
    :type: strDataToWrite String
    :param fAppend: Indicates if an append should occur (True == Append)
    :type: fAppend boolean
    """

    cMode = 'w'
    if fAppend:
      cMode = 'a'
    with open(strFileName,cMode) as f:
        f.write(strDataToWrite)
