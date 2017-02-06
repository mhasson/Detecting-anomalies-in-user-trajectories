#-*- coding: utf8
'''
Created on Oct 2, 2016

@author: zahran
'''
from MyEnums import *
from Metric import *
from HypTesting import *
from TestSample import *


#ANALYSIS_FILES_PATH = '/home/mohame11/pins_repins_fixedcat/allLikes/pvalues/'
#ANALYSIS_FILES_PATH = '/home/mohame11/pins_repins_fixedcat/injections/pvalues/'
#FILE_NAME = 'outlier_analysis_pvalues_'
#FILE_NAME = 'PARSED_pins_repins_win10_pinterest_INJECTED_SCORES_ANOMALY_ANALYSIS_'
    

class OutlierEvaluation:
    def __init__(self, allData, techType, hyp, metricType, pvalueTyp, alpha, testSetCountAdjust):
        self.allData = allData
        self.techType = techType
        self.hypType = hyp
        self.metricType = metricType
        self.pvalueTyp = pvalueTyp
        self.alpha = alpha
        self.testSetCountAdjust = testSetCountAdjust
        
        allTestsCount = 0
        for u in self.allData:
            allTestsCount += len(self.allData[u])
            
        self.allTestsCount = allTestsCount #this is the count of "B+1" actions sequences we have.
                        
        if(hyp == HYP.BONFERRONI):
            self.hypObj = Bonferroni(self.alpha, self.testSetCountAdjust, self.allTestsCount)
        elif(hyp == HYP.HOLMS):
            self.hypObj = Holms(self.alpha, self.testSetCountAdjust, self.allTestsCount)
        
        if(self.metricType == METRIC.CHI_SQUARE):
            self.metricObj = Chisq()
        elif(self.metricType == METRIC.REC_PREC_FSCORE):
            self.metricObj = rpf()
        elif(self.metricType == METRIC.FISHER):
            self.metricObj = Fisher()
            
               
        
        
                                
    def formOriginalSeq(self, tests):
        origSeq = list(tests[0].actions)  
        origGoldMarkers = list(tests[0].goldMarkers)
        for i in range(1,len(tests)):
            a = tests[i].actions[-1]
            g = tests[i].goldMarkers[-1]
            origSeq.append(a)
            origGoldMarkers.append(g)            
        return origSeq, origGoldMarkers
    
    
    
    def aggregateDecisions(self, actionDecisions):
        if(self.techType == TECHNIQUE.ALL_OR_NOTHING):
            for d in actionDecisions:
                if(d == DECISION.NORMAL):
                    return DECISION.NORMAL
            return DECISION.OUTLIER
            
        elif(self.techType == TECHNIQUE.ONE_IS_ENOUGH):
            for d in actionDecisions:
                if(d == DECISION.OUTLIER):
                    return DECISION.OUTLIER
            return DECISION.NORMAL
            
        elif(self.techType == TECHNIQUE.MAJORITY_VOTING):
            counts = {}
            mySet = set(actionDecisions)
            if(len(mySet) == 1):
                return actionDecisions[0]
            counts[DECISION.NORMAL] = actionDecisions.count(DECISION.NORMAL)
            counts[DECISION.OUTLIER] = actionDecisions.count(DECISION.OUTLIER)
            
            if(counts[DECISION.NORMAL] >= counts[DECISION.OUTLIER]):
                return DECISION.NORMAL
            return DECISION.OUTLIER
                        
            
    
    def evaluate(self):         
        if(self.testSetCountAdjust == False):   
            for u in self.allData:
                tests = self.allData[u]
                #print(u,len(tests),len(tests[0].actions))
                if(len(tests)>1):
                    originalSeq, originalGoldMarkers = self.formOriginalSeq(tests)
                    winSize = len(tests[0].PvaluesWithRanks)
                    decisionsForOriginalSeq = []
                    
                    for origIdx in range(len(originalSeq)):
                        firstSeqIdxAppear = origIdx // winSize  #the index of first seq this current action appeared in                   
                        firstIdxInFirstSeq = origIdx % winSize  #the index of current action in that seq
                        
                        idxInSeq = firstIdxInFirstSeq   
                        actionDecisions = []
                        
                        for seqIdx in range(firstSeqIdxAppear, len(tests)):                                                
                            if(idxInSeq < 0):
                                break
                            t = tests[seqIdx]
                            goldMarkers = t.goldMarkers                
                            if(self.pvalueTyp == PVALUE.WITH_RANKING):
                                pValues = t.PvaluesWithRanks
                            elif(self.pvalueTyp == PVALUE.WITHOUT_RANKING):
                                pValues = t.PvaluesWithoutRanks
                                
                            keySortedPvalues = sorted(pValues, key=lambda k: (-pValues[k], k), reverse=True)                                            
                            decisionVec = self.hypObj.classify(keySortedPvalues, pValues)                    
                            actionDecisions.append(decisionVec[idxInSeq])
                            
                            idxInSeq -= 1
                            
                        # now we have a list of decisions for the action at index=origIdx
                        # depending on the classification technique we pick only one decision out of the actionDecisions
                        finalDecision = self.aggregateDecisions(actionDecisions)
                        decisionsForOriginalSeq.append(finalDecision)
                                   
                    self.metricObj.update(decisionsForOriginalSeq, originalGoldMarkers)
                    
                elif(len(tests) == 1): # the number of sequences is 1, no need to get original sequences.
                    t = tests[0]
                    goldMarkers = t.goldMarkers    
                                
                    if(self.pvalueTyp == PVALUE.WITH_RANKING):
                        pValues = t.PvaluesWithRanks
                    elif(self.pvalueTyp == PVALUE.WITHOUT_RANKING):
                        pValues = t.PvaluesWithoutRanks
                        
                    keySortedPvalues = sorted(pValues, key=lambda k: (-pValues[k], k), reverse=True)
                    #print(len(keySortedPvalues), len(pValues))                                            
                    decisionVec = self.hypObj.classify(keySortedPvalues, pValues)  
                    
                    self.metricObj.update(decisionVec, goldMarkers)
                    
        #----------------------------------------------------------------------------------------------------------------------  
        #when self.testSetCountAdjust == True   
        else:
            allPvalues = {}
            for u in self.allData:
                tests = self.allData[u]
                for ti, t in enumerate(tests):
                    if(self.pvalueTyp == PVALUE.WITH_RANKING):
                        pValues = t.PvaluesWithRanks
                    elif(self.pvalueTyp == PVALUE.WITHOUT_RANKING):
                        pValues = t.PvaluesWithoutRanks
                    for p in pValues:
                        theKey = '_'.join([str(u),str(ti),str(p)])
                        allPvalues[theKey] = pValues[p]
            
            keySortedAllPvalues = sorted(allPvalues, key=lambda k: (-allPvalues[k], k), reverse=True)  #sort ascendingly
            
            for u in self.allData:
                tests = self.allData[u]
                originalSeq, originalGoldMarkers = self.formOriginalSeq(tests)
                winSize = len(tests[0].PvaluesWithRanks)
                decisionsForOriginalSeq = []
                
                for origIdx in range(len(originalSeq)):
                    firstSeqIdxAppear = origIdx // winSize  #the index of first seq this current action appeared in                   
                    firstIdxInFirstSeq = origIdx % winSize  #the index of current action in that seq
                    
                    idxInSeq = firstIdxInFirstSeq   
                    actionDecisions = []
                    
                    for seqIdx in range(firstSeqIdxAppear, len(tests)):                                                
                        if(idxInSeq < 0):
                            break
                        t = tests[seqIdx]
                        goldMarkers = t.goldMarkers                
                        if(self.pvalueTyp == PVALUE.WITH_RANKING):
                            pValues = t.PvaluesWithRanks
                        elif(self.pvalueTyp == PVALUE.WITHOUT_RANKING):
                            pValues = t.PvaluesWithoutRanks
                        
                        theKey = '_'.join([str(u), str(seqIdx), str(idxInSeq)])
                        rank = keySortedAllPvalues.index(theKey)
                        #keySortedPvalues = sorted(pValues, key=lambda k: (-pValues[k], k), reverse=True)                                            
                        #decisionVec = self.hypObj.classify(keySortedPvalues, pValues)                   
                        dec = self.hypObj.classifyOne(rank, keySortedAllPvalues, allPvalues)
                        actionDecisions.append(dec)
                        
                        idxInSeq -= 1
                        
                    # now we have a list of decisions for the action at index=origIdx
                    # depending on the classification technique we pick only one decision out of the actionDecisions
                    finalDecision = self.aggregateDecisions(actionDecisions)
                    decisionsForOriginalSeq.append(finalDecision)
                               
                self.metricObj.update(decisionsForOriginalSeq, originalGoldMarkers)
                
                
                
                
                            
        
        
    
    
    

def main():
       
    #ALPHA_NORANKING = np.arange(0.000005,0.1,0.005) # start=0, step=0.1, end=1 (exlusive)
    #ALPHA_RANKING = np.arange(0.000005,0.1,0.005)    
    
    
    ANALYSIS_FILES_PATH = '/home/mohame11/pins_repins_fixedcat/allLikes/pvalues_withWindow_log/'
    #ANALYSIS_FILES_PATH = '/scratch/snyder/m/mohame11/pins_repins_win4_fixedcat/allLikes/pvalues_3gram/'
    FILE_NAME = 'outlier_analysis_pvalues_'
    
    print('>>> Reading Data ...')
    allData = TestSample.parseAnalysisFiles(FILE_NAME, ANALYSIS_FILES_PATH)
    print('>>> Evaluating ...')
    
    actionAtBoundary = BOUNDARY.INCLUDE #NEED to BE ADDED
    
    #metricList = [METRIC.REC_PREC_FSCORE]
    metricList = [METRIC.FISHER]
    techList = [TECHNIQUE.ALL_OR_NOTHING,TECHNIQUE.MAJORITY_VOTING,TECHNIQUE.ONE_IS_ENOUGH]
    #alphaList = [5e-50, 5e-40, 5e-30, 5e-20, 5e-15, 5e-10, 5e-9, 5e-8, 5e-7, 5e-6, 5e-5, 5e-4, 5e-3, 5e-2, 5e-1]
    alphaList = [5e-10, 5e-9, 5e-8, 5e-7, 5e-6, 5e-5, 5e-4, 5e-3, 5e-2, 5e-1, 0.6, 0.7, 0.8, 0.9]
    hypList = [HYP.BONFERRONI, HYP.HOLMS]
    pvalueList = [PVALUE.WITHOUT_RANKING, PVALUE.WITH_RANKING]
    testSetCountAdjustList = [False]
    
    for metric in metricList:
        for pv in pvalueList:
            logger = open(ANALYSIS_FILES_PATH+str(metric)+'_'+str(pv),'w')
            for alpha in alphaList:            
                for tech in techList:                
                    for hyp in hypList:                                       
                        for tadj in testSetCountAdjustList:
                            
                            print(metric, pv,alpha,tech,hyp,tadj)
                            
                            ev = OutlierEvaluation(allData, tech, hyp, metric, pv, alpha, tadj)
                            ev.evaluate()   
                            
                            logger.write('alpha='+str(alpha))
                            logger.write(', '+str(tech))       
                            logger.write(', '+str(hyp))                                
                            logger.write(', TScountAdj='+str(tadj))
                            logger.write(': '+ev.metricObj.getSummary()+'\n')
                            logger.flush()
        logger.close()
        
        
  
    
main()    
print('DONE!')
