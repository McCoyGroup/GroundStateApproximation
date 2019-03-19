import numpy as np
import os
import usefulFunctions as use
import time
import scipy.linalg as sla
import itertools
import gc
import sys
import matplotlib as mpl
import multiprocessing

mpl.use('agg')
ProtonatedWaterTrimer = {'H7O3+','O3H7+', 'H7O3plus','H7O3', 'O3H7'}
ProtonatedWaterTetramer = {'H9O4+','O4H9+', 'H9O4plus','H9O4', 'O4H9'}
global ProtonatedWaterTrimer
au2wn=219474.63
au2ang=0.529177249
massConversionFactor=1.000000000000000000/6.02213670000e23/9.10938970000e-28
ang2bohr=1.88973
bohr2ang=1.000/ang2bohr
global massH
global massO
global massD
massH=1.00782503223
massD=2.0141017778
massO=15.99491561957
massO*=massConversionFactor


verbose=False



class HarmonicApproxSpectrum(object):
    def __init__(self,wfn,coords,dw,path,testName): #CHANGE THIS
        self.wfn=wfn
        self.coords=coords
        self.dw=dw
        self.nVibs=self.wfn.molecule.nVibs
        self.path=path
        self.testname = testName

    def LoadG(self,GfileName):
        print 'does ', GfileName, 'exist?'
        if not os.path.isfile(GfileName):
                print 'no!'
                gnm=self.calculateG(self.coords,self.dw)
                if 'test' not in GfileName:
                    np.savetxt(GfileName,gnm)
                else:
                    return gnm
        else:
            print 'yes! ^-^'
        G=np.loadtxt(GfileName)
        return G

    def calculateG(self,eckartRotatedCoords,descendantWeights):
        #RYAN - THE COORDINATES ARE NOT ACTUALLY ECKART ROTATED
        #Input is x which is a NAtoms x 3(coordinates) sized array
        #input is also dx, the perturbation size, usually .001                                                
        #output is the G matrix, which is a self.nVibs*self.nVibs sized array (there are self.nVibs internals)
        #(3N-6 x 3N-6)
        dx=1e-4
        gnm=np.zeros((self.nVibs,self.nVibs))
        start=time.time()
        sumDescendants=0
        mass=self.wfn.molecule.get_mass()
        print 'Start calculating G'
        #ocom, eVecs, kil = self.wfn.molecule.eckartRotate(eckartRotatedCoords)
        #eckartRotatedCoords = np.einsum('knj,kij->kni', eVecs.transpose(0, 2, 1), eckartRotatedCoords).transpose(0, 2, 1)

        threwOut=0
        print 'summing up the descendants', np.sum(descendantWeights)
        sumDescendants=sumDescendants+np.sum(descendantWeights)
        for atom in range(self.wfn.molecule.nAtoms):
            for coordinate in range(3):
                """WHERE INTERNAL COORDINATES ARE USED"""
                print 'dx number',atom*3+(coordinate+1), 'atom:',atom, 'coordinate',coordinate
                deltax=np.zeros((eckartRotatedCoords.shape))
                deltax[:,atom,coordinate]=deltax[:,atom,coordinate]+dx #perturbs the x,y,z coordinate of the atom of interest
                #ECKART ROTATION DOES NOT NEED TO HAPPEN YET

                coordPlus=self.wfn.molecule.SymInternals(eckartRotatedCoords+deltax,False) #true = rotate to frame before adjusting axis coordinates.

                coordMinus=self.wfn.molecule.SymInternals(eckartRotatedCoords-deltax,False)
                partialderv=(coordPlus-coordMinus)/(2.0*dx) #Discretizing stuff - derivative with respect to our perturbation

                timegnm=time.time()

                LastPartialDerv2MassWeighted=0
                for i, pd in enumerate(partialderv):
                    partialderv2 = np.outer(pd, pd)
                    # print 'zeros ?',partialderv2prime[i*self.nVibs:(i+1)*self.nVibs,i*self.nVibs:(i+1)*self.nVibs]-partialderv2
                    tempPartialDerv2MassWeighted = partialderv2 * descendantWeights[i] / mass[atom]

                    if np.any(tempPartialDerv2MassWeighted > 1000000.0 * dx):  # (gnm[9,9]/(np.sum(self.Descendants[:i]))): $$$$$
                        print 'atom', atom, 'coordinate', coordinate, i, 'temp', np.transpose(
                            np.where(tempPartialDerv2MassWeighted > 10000.0 * dx)), 'is too big'

                        print 'tempPartialDerv2MassWeighted', tempPartialDerv2MassWeighted, '\n Descendants', \
                        descendantWeights[i]
                        print 'coordinates \n', eckartRotatedCoords[i], '\n', eckartRotatedCoords[i] + deltax[i], '\n', \
                        eckartRotatedCoords[i] - deltax[i]
                        print 'eckart rotate \n', coordPlus[i], coordMinus[i]
                        print 'pd \n', pd

                        gnm = gnm + LastPartialDerv2MassWeighted
                        threwOut = threwOut + 1
                    else:
                        gnm = gnm + tempPartialDerv2MassWeighted
                        LastPartialDerv2MassWeighted = 1.0 * tempPartialDerv2MassWeighted
                # for i,pd in enumerate(partialderv): #i = enum num
                #     partialderv2=np.outer(pd,pd)
                #     #print 'zeros ?',partialderv2prime[i*self.nVibs:(i+1)*self.nVibs,i*self.nVibs:(i+1)*self.nVibs]-partialderv2
                #     tempPartialDerv2MassWeighted=partialderv2*descendantWeights[i]/mass[atom] #24x24
                #     if np.any(tempPartialDerv2MassWeighted>1000000.0*dx):#(gnm[9,9]/(np.sum(self.Descendants[:i]))): $$$$$
                #         print 'Problem!'
                #         listOfpartials = np.transpose(np.where(tempPartialDerv2MassWeighted > 1000000.0 * dx))
                #         print tempPartialDerv2MassWeighted[np.where((tempPartialDerv2MassWeighted > 1000000.0 * dx))]
                #         print 'atom',atom, 'coordinate',coordinate, i,'temp',np.transpose(np.where(tempPartialDerv2MassWeighted>10000.0*dx)),'is too big'
                #         print 'walker',i
                #         for ptls in range(len(listOfpartials)):
                #            print listOfpartials[ptls,0],listOfpartials[ptls,1]
                #            print self.wfn.molecule.internalName[listOfpartials[ptls,0]],self.wfn.molecule.internalName[listOfpartials[ptls,1]]
                #            cdm=coordMinus[i,listOfpartials[ptls,0]],coordMinus[i,listOfpartials[ptls,1]]
                #            cdp=coordPlus[i,listOfpartials[ptls,0]],coordPlus[i,listOfpartials[ptls,1]]
                #            #print 'Minus: ',cdm
                #            #print 'Plus: ',cdp
                #            print "Thing that's >100",tempPartialDerv2MassWeighted[listOfpartials[ptls,0],listOfpartials[ptls,1]],self.wfn.molecule.internalName[coordinate]
                #         print 'tempPartialDerv2MassWeighted', tempPartialDerv2MassWeighted, '\n Descendants', descendantWeights[i]
                #         print 'max = ', np.amax(tempPartialDerv2MassWeighted)
                #         print 'coordinates \n', eckartRotatedCoords[i],'\n', eckartRotatedCoords[i]+deltax[i],'\n',eckartRotatedCoords[i]-deltax[i]
                #         print 'eckart rotate \n', coordPlus[i], coordMinus[i]
                #         print 'pd \n',pd
                #         gnm=gnm+LastPartialDerv2MassWeighted
                #         threwOut=threwOut+1
                #     else:
                #         gnm=gnm+tempPartialDerv2MassWeighted
                #         #LastPartialDerv2MassWEighted=1.0*tempPartialDerv2MassWeighted

            print 'gnmtiminging:',time.time()-timegnm
        print "THREW OUT ", threwOut, " walkers :-("
        print 'timing for G matrix', time.time()-start
        print 'dividing by ',sumDescendants
        gnm=gnm/sumDescendants
        return gnm

    def diagonalizeRootG(self,G):
        w,v=np.linalg.eigh(G)
        #print w,v
        #octomom
        #vinv=np.linalg.inv(v)
        invRootDiagG=np.diag(1.0/np.sqrt(w))  #1.0/rootDiagG  #MAYBE THIS IS OK??                                                                                       
        for i,ValinvRootDiagG in enumerate(invRootDiagG):#range(self.nVibs):                                                                                            
            if verbose: print 'alp[',i,']',ValinvRootDiagG[i]
        invRootG=np.dot(v,np.dot(invRootDiagG,v.transpose()))
        #invG=np.dot(invRootG,invRootG.transpose())
        #checkG=np.linalg.inv(invG)
        #self.GHalfInv=invRootG
        return  invRootG

    def calculateSecondMoments(self,x,dw,setOfWalkers):
        #calculate average internals
        print 'Calculating moments . . .'
        internals=self.wfn.molecule.SymInternals(x)
        averageInternals=np.average(internals,weights=dw,axis=0)
        np.savetxt('averageInternals_'+setOfWalkers,averageInternals)
        #calculate moments
        print 'averageInternals: ',zip(self.wfn.molecule.internalName,averageInternals)
        moments=internals-averageInternals
        print 'Moments: ', moments
        #calculate second moments
        walkerSize =len(dw)
        print 'calculate second moments'
        # if os.path.isfile('mmap'):
        #     os.remove('mmap')
        # if os.path.isfile('smap'):
        #     os.remove('smap')
        # if os.path.isfile('dmap'):
        #     os.remove('dmap')

        #mmap = np.memmap('mmap', dtype='float64', mode='w+', shape=(int(walkerSize), int(self.nVibs)))
        #mmap[:] = moments[:]
        #mmap.flush()
        #del mmap
        dmap = np.memmap('dmap'+setOfWalkers, dtype='float64', mode='w+', shape=(int(walkerSize)))
        dmap[:] = dw[:]
        dmap.flush()
        del dw
        del dmap
        gc.collect()
        #mh = np.memmap('mmap', dtype='float64', mode='r', shape=(int(walkerSize), int(self.nVibs)))
        sh = np.memmap('smap'+setOfWalkers, dtype='float64', mode='w+', shape=(int(walkerSize), int(self.nVibs),int(self.nVibs)))
        print 'walkerSize',walkerSize
        if walkerSize > 1000000:
            chunkSize=500000
        else:
            chunkSize=100
        cycle = np.arange(0,walkerSize,chunkSize)
        last=False
        a=time.time()
        for stt in cycle:
            print time.time()-a
            print stt
            k=stt+chunkSize
            if k > walkerSize-chunkSize:
                last=True
            if not last:
                sh[stt:k,:,:]=moments[stt:k,:,np.newaxis]*moments[stt:k,np.newaxis,:]
            else:
                sh[stt:,:,:]=moments[stt:,:,np.newaxis]*moments[stt:,np.newaxis,:]
        sh.flush()
        del sh
        #del mh
        print 'returning moments...'
        return moments

    def overlapMatrix(self,q,dw,poE,walkerSet):
        lg = open("overlapLog.txt","w+")
        potE = np.copy(poE)*au2wn
        #Csontruct constants and on diagonal elements
        a = np.average(q * q * q / np.average(q * q, axis=0, weights=dw), axis=0, weights=dw) * (1 / np.average(q * q, axis=0, weights=dw))
        b = -1 / np.average(q * q, axis=0, weights=dw)
        #Construct Overlap Matrix
        #Construct diagonal elements
        lg.write('Construct Diagonal Elements\n')
        dgnl2=[]
        dgnl2.append(1)
        #dgnl.append(1) #ground state with itself
        for y in range(self.nVibs*2):
            if y < self.nVibs: #Fundamentals
                #dgnl.append(np.average(q2[:,y],weights=dw))
                dgnl2.append(np.average((q*q)[:,y],weights=dw))
            else: #Overtones
                a1sqrt=1+a[y-self.nVibs]*(q[:,y-self.nVibs])+b[y-self.nVibs]*(q[:,y-self.nVibs])*(q[:,y-self.nVibs])
                a1 =  np.average(a1sqrt*a1sqrt,weights=dw)
                #dgnl.append(a1)
                dgnl2.append(a1)
        del a1sqrt
        lg.write('time for on diag combos')
        ########combos for overlap 2
        for (x,y) in itertools.combinations(q.T,2):
            a2p=np.average(x*x*y*y,weights=dw)
            dgnl2.append(a2p)
        #np.savetxt("dgnl2",dgnl2)

        #############Overlap matrix constructed######################
        overlap2=np.diag(dgnl2)
        ham2 = np.diag(np.zeros(len(dgnl2)))
        #fig = plt.figure()
        #plt.matshow(overlap2)
        #plt.colorbar()
        #plt.savefig("overlapBegin.png")
        #plt.close()
        ############Off diagonal Elements#############################
        #q
        # bq^2+aq+1 ASDF
        start = time.time()
        bq2aq1=1+a*q+b*q*q
        del a
        del b
        gc.collect()
        lg.write('Construct Off-Diagonal Elements\n')
        lg.write('Funds w ground\n')
        overlap2[0,1:self.nVibs+1]=np.average(q,axis=0,weights=dw)
        ham2[0, 1:self.nVibs + 1] = np.average(q*potE[:,np.newaxis], axis=0, weights=dw)
        overlap2[0,self.nVibs+1:self.nVibs*2+1] = np.average(bq2aq1, axis=0, weights=dw)
        ham2[0, self.nVibs + 1:self.nVibs * 2 + 1] = np.average(bq2aq1*potE[:,np.newaxis], axis=0, weights=dw)
        #combinations
        lg.write('Combinations with ground\n')
        nvibs2 = self.nVibs*2
        vbo=np.flip(np.arange(self.nVibs+1))
        curI = nvibs2+1
        nxtI = curI+self.nVibs-1
        for combo in range(self.nVibs):
            overlap2[0,curI:nxtI]=np.average(q[:,combo,np.newaxis]*q[:,(combo+1):],axis=0,weights=dw)
            ham2[0, curI:nxtI] = np.average(q[:, combo, np.newaxis]*q[:, (combo + 1):]*potE[:,np.newaxis], axis=0, weights=dw)
            curI = nxtI
            nxtI += vbo[combo+1]-1
        lg.write("done\n")
        ##Fundamentals with other funds - already calculated
        lg.write('Funds with other Funds\n')
        pst=np.triu_indices_from(overlap2[1:self.nVibs+1,1:self.nVibs+1],k=1)
        af=pst[0]+1
        bf=pst[1]+1
        overlap2[tuple((af,bf))] = np.copy(overlap2[0,nvibs2+1:])
        ham2[tuple((af,bf))] = np.copy(ham2[0,nvibs2+1:])
        lg.write("done\n")
        ##Funds with overtones
        ##MEMMAPS
        # overtones with other overtones
        lg.write("Ovs with Ovs\n")
        for combo in range(self.nVibs):
            lg.write('combo_'+str(combo))
            #asdf=np.average(bq2aq1[:, combo, np.newaxis] * bq2aq1[:, (combo + 1):], axis=0, weights=dw)
            overlap2[self.nVibs + combo + 1, self.nVibs + combo + 2:nvibs2 + 1] = np.average(bq2aq1[:, combo, np.newaxis] * bq2aq1[:, (combo + 1):], axis=0, weights=dw)
            ham2[self.nVibs + combo + 1, self.nVibs + combo + 2:nvibs2 + 1] = np.average(bq2aq1[:, combo, np.newaxis]*bq2aq1[:, (combo + 1):]*potE[:,np.newaxis], axis=0, weights=dw)
            lg.write('loop')
        lg.write('done. overs with themselves\n')

        #Funds with Overtones
        hav = np.zeros((self.nVibs,self.nVibs))
        hamhav = np.zeros((self.nVibs,self.nVibs))
        for ind in range(self.nVibs):
            hav[ind,:]=np.average(q[:,ind,np.newaxis]*bq2aq1,weights=dw,axis=0)
            hamhav[ind,:]=np.average(q[:,ind,np.newaxis]*bq2aq1*potE[:,np.newaxis],weights=dw,axis=0)
        overlap2[1:self.nVibs + 1, self.nVibs + 1:nvibs2 + 1] = hav
        ham2[1:self.nVibs + 1, self.nVibs + 1:nvibs2 + 1] = hamhav

        # funds with combos and overtones with combos
        bigMem = False
        if bigMem:
            sumDw = np.sum(dw)
            nvibs2 = self.nVibs * 2
            print 'bigMemActivated'
            lnsize = int((self.nVibs * self.nVibs - self.nVibs) / 2.)
            lm = np.zeros((len(q), lnsize))
            for combo in range(self.nVibs):
                if combo == 0:
                    prev = 0
                print prev
                print prev + self.nVibs - combo - 1
                lm[:, prev:(prev + self.nVibs - combo - 1)] = q[:, combo, np.newaxis] * q[:,(combo + 1):]
                prev += self.nVibs - 1 - combo
            # fuco = np.sum(q[:, :, np.newaxis] * lm[:, np.newaxis, :] * dw[:, np.newaxis, np.newaxis],axis=0)
            # ovco = np.sum(bq2aq1[:, :, np.newaxis] * lm[:, np.newaxis, :] * dw[:, np.newaxis, np.newaxis],axis=0)
            # hfuco = np.sum(q[:, :, np.newaxis] * lm[:, np.newaxis, :] * potE[:, np.newaxis,np.newaxis] * dw[:,np.newaxis,np.newaxis],axis=0)
            # hovco = np.sum(bq2aq1[:, :, np.newaxis] * lm[:, np.newaxis, :] * potE[:, np.newaxis,np.newaxis] * dw[:,np.newaxis,np.newaxis],axis=0)
            # coco = np.sum(lm[:, :, np.newaxis] * lm[:, np.newaxis, :] * dw[:, np.newaxis, np.newaxis], axis=0)
            # hcoco = np.sum(lm[:, :, np.newaxis] * lm[:, np.newaxis, :] * potE[:, np.newaxis, np.newaxis] * dw[:,np.newaxis,np.newaxis],axis=0)
            ovlas = np.triu_indices_from(overlap2[nvibs2 + 1:, nvibs2 + 1:], k=1)
            g = ovlas[0] + nvibs2+1
            h = ovlas[1] + nvibs2+1
            asco = np.triu_indices_from(np.zeros((lnsize,lnsize)), k=1)
            overlap2[tuple((g, h))] = np.sum(lm[:, :, np.newaxis] * lm[:, np.newaxis, :] * dw[:, np.newaxis, np.newaxis], axis=0)[asco] / sumDw
            overlap2[1:self.nVibs + 1, self.nVibs * 2 + 1:] = np.sum(q[:, :, np.newaxis] * lm[:, np.newaxis, :] * dw[:, np.newaxis, np.newaxis],axis=0) / sumDw  # FC
            overlap2[self.nVibs + 1:2 * self.nVibs + 1, self.nVibs * 2 + 1:] = np.sum(bq2aq1[:, :, np.newaxis] * lm[:, np.newaxis, :] * dw[:, np.newaxis, np.newaxis],axis=0) / sumDw
            ham2[tuple((g, h))] = np.sum(lm[:, :, np.newaxis] * lm[:, np.newaxis, :] * potE[:, np.newaxis, np.newaxis] * dw[:,np.newaxis,np.newaxis],axis=0)[asco] / sumDw
            ham2[1:self.nVibs + 1, self.nVibs * 2 + 1:] = np.sum(q[:, :, np.newaxis] * lm[:, np.newaxis, :] * potE[:, np.newaxis,np.newaxis] * dw[:,np.newaxis,np.newaxis],axis=0) / sumDw  # FC
            ham2[self.nVibs + 1:2 * self.nVibs + 1, self.nVibs * 2 + 1:] = np.sum(bq2aq1[:, :, np.newaxis] * lm[:, np.newaxis, :] * potE[:, np.newaxis,np.newaxis] * dw[:,np.newaxis,np.newaxis],axis=0) / sumDw
        else:
            print 'smol Mem Activated'
            lst=[]
            for o, t in itertools.combinations(np.arange(self.nVibs), 2):
                lst.append((o, t))
            ct=0
            print len(lst)
            lg.write('funds and overs with combos\n')
            for (i,j) in lst:
                print ct
                overlap2[1:self.nVibs + 1,self.nVibs * 2 + 1+ct]=np.average(q*q[:,i,np.newaxis]*q[:,j,np.newaxis],weights=dw,axis=0)
                overlap2[self.nVibs+1:2*self.nVibs + 1, self.nVibs * 2 + 1+ct] = np.average(bq2aq1*q[:, i, np.newaxis] * q[:, j, np.newaxis], weights=dw, axis=0)
                ham2[1:self.nVibs + 1, self.nVibs * 2 + 1 + ct] = np.average(
                    q * q[:, i, np.newaxis] * q[:, j, np.newaxis]*potE[:,np.newaxis], weights=dw, axis=0)
                ham2[self.nVibs + 1:2 * self.nVibs + 1, self.nVibs * 2 + 1 + ct] = np.average(
                    bq2aq1 * q[:, i, np.newaxis] * q[:, j, np.newaxis]*potE[:,np.newaxis], weights=dw, axis=0)
                ct+=1
            print 'hello'
            lg.write('combos with combos\n')
            #combos with combos
            ovlas = np.triu_indices_from(overlap2[nvibs2 + 1:, nvibs2 + 1:], k=1)
            g = ovlas[0]
            h = ovlas[1]
            g += nvibs2 + 1
            h += nvibs2 + 1
            ct=0
            for [(w, x), (y, z)] in itertools.combinations(lst, 2):
                overlap2[tuple((g[ct], h[ct]))] = np.average(q[:,w] * q[:,x] * q[:,y] * q[:,z], weights=dw)
                ham2[tuple((g[ct], h[ct]))] = np.average(q[:, w] * q[:, x] * q[:, y] * q[:, z]*potE, weights=dw)
                ct += 1
            print 'total time off diags', time.time()-start
        return ham2,overlap2

    def calculateSpectrum(self, coords,dw,GfileName,pe,dips,setOfWalkers,testName,kill,ecked,diPath):
        sumDw = np.sum(dw)
        #Equations are referenced from McCoy, Diken, and Johnson. JPC A 2009,113,7346-7352
        #print 'I better be calculating the spectrum from ECKART ROTATED coordinates!'
        """Commence getting our modified descendent weights"""
        print 'Commence Calculate Spectrum Function'
        #dipoleMoments = np.zeros(np.shape(dips))

        print 'getting eckarted dipole moments. . .'
        # com, eckVecs = self.wfn.molecule.eckartRotate(coords)
        #print dips
        if testName == 'oxEck':
            justO = True
        else:
            justO = False
        if not ecked:
            com, eckVecs, killList = self.wfn.molecule.eckartRotate(coords, justO)
            dips = dips - com  # added this to shift dipole to center of mass before eckart roatation - translation of dipole should NOT matter
            print 'killList = '+str(len(killList))+' Walkers out of ' + str(len(dw))
            dipoleMoments = np.zeros(np.shape(dips))
            print 'dips shifted to COM: ', dips[0]
            for den in range(dips.shape[0]):
                dipoleMoments[den] = np.dot(dips[den],eckVecs[den])
                #dipoleMoments2[b] = np.dot(eckVecs[b],dips[b]) #This definitely isn't right
            print 'dipole moment - after eckart rotation: ', dipoleMoments[0]
            np.save(diPath+'eng_dip_'+setOfWalkers+'_eckart.npy',np.column_stack((pe,dipoleMoments)))
            del dips
        else:
            dipoleMoments = dips
            del dips
        #dips = dips*ang2bohr
        #First, What is the G Matrix for this set of walkers based on the SymInternals coordinates
        if not os.path.isfile('q_'+setOfWalkers+'.npy'):
            self.G=self.LoadG(GfileName)
            moments=self.calculateSecondMoments(coords, dw,setOfWalkers)
            q,q2=self.calculateQCoordinates(moments,dw,GfileName,setOfWalkers)
            print 'done with normal modes'
            #q4ave=np.average(q4,axis=0,weights=dw)
            q2ave=np.average(q2,axis=0,weights=dw)
            qave =np.average(q,axis=0,weights=dw)
            #print q.shape
            print '/\/\/\/\/\/\/\/\/\/\ '
            print 'some averages',
            print 'q\n',qave
            print 'q^2 \n',q2ave #average of q-squared
            #print 'q^4 \n',q4ave
            print '/\/\/\/\/\/\/\/\/\/\ '
            if 'test' not in setOfWalkers:
                np.save("q_"+setOfWalkers+".npy",q)
                np.save("q2_"+setOfWalkers+".npy",q2)
        else:
            print 'loading qs from file'
            q=np.load('q_'+setOfWalkers+'.npy')
            q2=np.load('q2_'+setOfWalkers+'.npy')
            q2ave = np.average(q2, axis=0, weights=dw)
            qave = np.average(q, axis=0, weights=dw)
        #Now calculate the Potential energy
        print 'calculating PE'
        potentialEnergy=self.calculatePotentialEnergy(coords,pe)
        print 'Potential Energy', potentialEnergy
        overlapTime=True
        if overlapTime:
            ham2,overlap2=self.overlapMatrix(q,dw,potentialEnergy,setOfWalkers)
            dov = np.diagonal(overlap2)
            overlap2 = overlap2 / np.sqrt(dov[:,None])
            overlap2 = overlap2 / np.sqrt(dov)
            ham2 = ham2 / np.sqrt(dov[:,None])
            ham2 = ham2 / np.sqrt(dov)
            overlap2 = overlap2+overlap2.T-np.eye(len(overlap2))
            print 'Hammie and Overlap Man are Constructed. Nearing the end...'
            print 'abs overlap Max Min', np.amax(np.abs(overlap2)),np.amin(np.abs(overlap2))
            ham2 = ham2+ham2.T #nothing on diagonal
            overlapMs = self.path+'redH/'
            np.savetxt(overlapMs+'overlapMatrix2_' + setOfWalkers + testName + kill + '.dat', overlap2)
            np.savetxt(overlapMs+'offDiagonalCouplingsInPotential2_' + setOfWalkers + testName + kill + '.dat', ham2)
        #V_0=<0|V|0>
        print 'overlap matrix done'
        print 'Potential Energy',potentialEnergy
        V_0=np.average(potentialEnergy[:,None],axis=0,weights=dw)

        # Vq= <1_q|V|1_q> bra:state with one quanta in mode q, ket: state with one quanta in mode q
        Vq=np.average(potentialEnergy[:,None]*q2,axis=0,weights=dw)

        #Vq2d=<q^2Vq^2> (<> is an average of the descendant weights)
        Vq2d=np.zeros((self.nVibs,self.nVibs)) # one quanta in one mode and 1 quanta in another mode

        #q2ave2d=<q^2 q^2> (<> is an average of the descendant weights)  
        q2ave2d=np.zeros((self.nVibs,self.nVibs))

        for i in range(coords.shape[0]):
            Vq2d=Vq2d+np.outer(q2[i],potentialEnergy[i]*q2[i])*dw[i]
            q2ave2d=q2ave2d+np.outer(q2[i],q2[i])*dw[i]
        Vq2d=Vq2d/np.sum(dw)
        q2ave2d=q2ave2d/np.sum(dw)        
        
        #Now calculate the kinetic energy
        print 'ZPE: average v_0',V_0*au2wn
        print 'Vq', Vq*au2wn

        alpha=q2ave/(np.average(q*q*q*q,weights=dw,axis=0)-q2ave**2) # Equation #11
        alphaPrime=0.5/q2ave   #Equation in text after #8
        #        print 'how similar are these?', zip(alpha,alphaPrime) Still a mystery to me why there were 2 dfns of alpha


        #kineticEnergy= hbar**2 nquanta alpha/(2 mass)
        Tq=1.0**2*1.0*alpha/(2.0*1.0) #Equation #10
        
        Tq2d=np.zeros((self.nVibs,self.nVibs)) #Tij=Ti+Tj
        #Finish calculate the potential and kinetic energy for the combination and overtone bands 
        #put Equation 8 into equation 4, algebra...
        for ivibmode in range(self.nVibs): #combination band calculations + overtones (i=j)
            for jvibmode in range(ivibmode):
                Vq2d[ivibmode,jvibmode]=Vq2d[ivibmode,jvibmode]/q2ave2d[ivibmode,jvibmode]
                Vq2d[jvibmode,ivibmode]=Vq2d[jvibmode,ivibmode]/q2ave2d[jvibmode,ivibmode]
                Tq2d[ivibmode,jvibmode]=Tq[ivibmode]+Tq[jvibmode]
                Tq2d[jvibmode,ivibmode]=Tq2d[ivibmode,jvibmode]
            #Vq2d[ivibmode,ivibmode]=Vq2d[ivibmode,ivibmode]*4.0*alpha[ivibmode]**2-Vq[ivibmode]*4.0*alpha[ivibmode]+V_0
            #Vq2d[ivibmode,ivibmode]=Vq2d[ivibmode,ivibmode]/(4.0*alpha[ivibmode]**2*q2ave2d[ivibmode,ivibmode]-4.0*alpha[ivibmode]*q2ave[ivibmode]+1.0)
            #Vq2d[ivibmode, ivibmode] = Vq2d[ivibmode, ivibmode] * 4.0 * alpha[ivibmode] ** 2 - Vq[ivibmode] * 4.0 *alpha[ivibmode] + V_0
            Tq2d[ivibmode,ivibmode]=Tq[ivibmode]*2.0
        #Let's get overtones set up
        a = np.average(q*q*q / np.average(q*q,axis=0,weights=dw),axis=0,weights=dw) * (1/np.average(q*q,axis=0,weights=dw))
        b = -1/np.average(q*q,axis=0,weights=dw)
        vovers = np.average((1+a*q+b*q*q)*potentialEnergy[:,None]*(1+a*q+b*q*q),axis=0,weights=dw)
        vovers /= (np.average(np.square(1+a*q+b*q*q),axis=0,weights=dw))
        np.fill_diagonal(Vq2d,vovers)
        print 'overtone combo potential',Vq2d
        #Energy is V+T, don't forget to subtract off the ZPE
            #Eq2d=np.zeros((self.nVibs,self.nVibs))
        Eq2d=(Vq2d+Tq2d)-V_0 #related to frequencies later on
        Eq=(Vq/q2ave+Tq)-V_0
        #noKE_funds = Vq/q2ave - V_0
        #noKE_combos = Vq2d-V_0
        #Lastly, the dipole moments to calculate the intensities! Ryan - Do you even have to eckart the molecule, why not just eckart rotate the dipole moment?

        #dipoleMoments=self.wfn.molecule.dipole(coords)
        #notRotateddipoleMoments = dips
        #dips =self.wfn.molecule.rotateDipoleToFrame(coords, dips) #NEED TO HAVE THIS SO THAT MY ECKART ROTATION OF THE COORDINATES (WHICH ARE IN XY PLANE) MATCH THE ECKART ROTATION OF THE DIPOLE

        #dips =self.wfn.molecule.loadDips(dips) #get rotated dipoles



        #stop
        #print 'getting eckarted dipole moments. . .'
        #dipoleMoments = self.wfn.molecule.rotateDipoleToFrame(coords,dips)
        #print dipoleMoments

        #print 'Dipole Moments!: ',dipoleMoments
        averageDipoleMoment_0=np.average(dipoleMoments,axis=0,weights=dw)
        print 'Average Dipole Moment!: ',averageDipoleMoment_0
        #aMu_i=<1_i|dipoleMoment|0>=Sum_n^walkers(Dipole_n*q_i*dw_n)/Sum(dw) #Equation 4 for \psi_n=\psi_1
        aMu=np.zeros((3,self.nVibs))  
        #aMu2d_{i,j}=<1_i,1_j|dipoleMoment|0>=Sum_n^walkers(Dipole_n*q_i*q_j*dw_n)/Sum(dw) #Equation 4 for \psi_n=\psi_{1,1}
        aMu2d=np.zeros((3,self.nVibs,self.nVibs))
        print 'dip:'
        print dipoleMoments.shape
        #q = nWalkers x 24
        #dw = nWalkers
        #dipoleMoments = nWalkers x 3
        #aMu = dipole (x) -Q coord - 24x3
        for P,R,d in zip(dipoleMoments,q,dw): #P = dipole moment (nx3), R = q coordinate (3n-6x1), d = descendent wight (n)
            aMu=aMu+np.outer(P,-R)*d  #off by a sign change for some reason so I changed it to be -R instead of R...I guess P could be backwards?
            #aMu=aMu+np.outer(P,R)*d  #Ryan - this doesn't change the results, as of right now (7/19/18)
            temp=np.outer(R,R)        #aMu += Dipole.coordinate * DQ
            temp=temp.reshape((self.nVibs*self.nVibs,1))
            aMu2d=aMu2d+(np.outer(P,temp).reshape((3,self.nVibs,self.nVibs)))*d
        #aMu = 24x3 dipole contribution in that coordinate?
        aMu=aMu/np.sum(dw)
        aMu2d=aMu2d/np.sum(dw)

        #np.savetxt("WtvsMu-qs-a.data",zip(dw,np.sum(dipoleMoments**2,axis=1),q[:,5],q[:,6]))

        aMu=aMu.transpose() #3x24 instead of 24x3
        aMu2d=aMu2d.transpose()  #switches around the axes 24x24x3

        magAvgMu=np.zeros(self.nVibs)

        #Finding |<1_i|dipoleMoment|0>|^2
        """Getting intensity!"""
        #print 'aMu: ', aMu.shape,aMu
        #np.savetxt('aMuDividedBySqrt_q2',aMu/np.sqrt(q2ave))
        for m,mode in enumerate(aMu): #eq 4
            magAvgMu[m]=magAvgMu[m]+(mode[0]**2+mode[1]**2+mode[2]**2)/(q2ave[m])  #     += mu_x^2+mu_y^2+mu_z^2 /<q^2>
        print magAvgMu
        #stop

        magMu2d=np.zeros((self.nVibs,self.nVibs))
        #Finding |<1_i,1_j|dipoleMoment|0>|^2
        for ivibmode in range(self.nVibs):
            #aMu2d[ivibmode,ivibmode]=2*alpha[ivibmode]*aMu2d[ivibmode,ivibmode]-averageDipoleMoment_0
            #magMu2d[ivibmode,ivibmode]=np.sum(aMu2d[ivibmode,ivibmode]**2)
            #magMu2d[ivibmode,ivibmode]=magMu2d[ivibmode,ivibmode]/(q2ave2d[ivibmode,ivibmode]*4.0*alpha[ivibmode]**2-4.0*alpha[ivibmode]*q2ave[ivibmode]+1.0)
            #magMu2d[ivibmode, ivibmode] = magMu2d[ivibmode, ivibmode]/(q2ave2d[ivibmode, ivibmode]*4.0*alpha[ivibmode]**2-4.0*alpha[ivibmode]*q2ave[ivibmode]+1.0)
            for jvibmode in range(ivibmode):
                magMu2d[ivibmode,jvibmode]=np.sum(aMu2d[ivibmode,jvibmode]**2)
                magMu2d[ivibmode,jvibmode]=magMu2d[ivibmode,jvibmode]/q2ave2d[ivibmode,jvibmode]
                magMu2d[jvibmode,ivibmode]=magMu2d[ivibmode,jvibmode]

        #First: get values I want, which are not the magnitude squared, just the:
        #Fundamentals: <i=1 | u | 0>
        mu10 = aMu/ np.sqrt(q2ave)[:,None]
        overlapMs = self.path+'redH/'
        np.savetxt(overlapMs+'1mu0' + setOfWalkers + testName + kill,mu10)
        #Overtones: <i=2|u|0>
        #isthisok = np.diagonal(aMu2d).T #it is.
        #f = np.average(np.square(2*alpha*q2-1),axis=0,weights=dw)

        #f = np.average(np.square(1+a*(q)+b*np.square(q)),axis=0,weights=dw)
        #sq_ov2 = np.sqrt(f)
        #mu20 = (2*alpha*np.diagonal(aMu2d)-averageDipoleMoment_0[:,None])/sq_ov2
        #mu20 = () / sq_ov2

        #Overtone intensities are currently incorrect, let's do it from scratch
        overpoly = (b*q2+a*q+1)
        rMu20 = np.zeros((3,self.nVibs))
        for walker in range(len(dipoleMoments)):
            rMu20 += np.outer(dipoleMoments[walker],overpoly[walker])*dw[walker]
        rMu20 /= np.sum(dw)
        rMu20 /= np.sqrt(np.average(np.square(b*q2+a*q+1),weights=dw,axis=0))
        rMu20=rMu20.T
        magRMu20 = np.sum(np.square(rMu20),axis=1)
        np.savetxt(overlapMs+'2mu0' + setOfWalkers + testName + kill,rMu20)
        np.fill_diagonal(magMu2d,magRMu20)

        #Combinations: <i=1,j=1|u|0>
        tupz = []
        for i in range(self.nVibs):
            for j in range(i):
                tupz.append([i,j])
        fMu = np.zeros((len(tupz),3))
        fMup= np.zeros((len(tupz),3))
        ct=0
        avg2pairs = np.zeros(len(tupz))
        avg2pairsp = np.zeros(len(tupz))

        for glomp in tupz:
            fMu[ct,:] = aMu2d[glomp[0],glomp[1]]
            avg2pairs[ct] = q2ave2d[glomp[0],glomp[1]]
            ct+=1
        ct=0
        for (x,y) in itertools.combinations(np.arange(self.nVibs),2):
            fMup[ct,:] = aMu2d[x,y]
            avg2pairsp[ct] = q2ave2d[x,y]
            ct+=1
        mu110 = fMu/avg2pairs[:,None]
        mu110p = fMup/avg2pairsp[:,None]

        np.savetxt(overlapMs+'11mu0'+ setOfWalkers + testName + kill,mu110)
        np.savetxt(overlapMs+'11mu0p'+ setOfWalkers + testName + kill,mu110p)
        #want all of the things I need to magnitude:
        #
        print 'done'
        
        #######################################################################################################

        print "m alpha   alpha'=0.5/<q2>        Vq            Vq/q2ave      Tq            Eq          |<1|dipole|0>|"
        for i in range(9):
            print i, alpha[i], alphaPrime[i],au2wn*Vq[i], au2wn*Vq[i], Vq[i]/q2ave[i]*au2wn, Eq[i]*au2wn, magAvgMu[i]

        print 'energies!', zip(Vq2d[0]*au2wn,Tq2d[0]*au2wn,Eq2d[0]*au2wn)

        print 'Spectrum Info'
        #fundamentalFileName=self.path+'fundamentalsJUSTPOTENTIAL'+testName+'.data'
        comboFileName=self.path+'combinationOverrtone_'+setOfWalkers+testName+kill+'.data'
        #fundamentalFile=open(fundamentalFileName,'w')
        comboFile=open(comboFileName,'w')
        comboFile2=open(comboFileName+'2','w')
        #justVComboFile = open(comboFileName+"_justV",'w')
        """magAvgMu = Intensity for fundamentals
           magMu2d  = Intensity for combination and overtone bands"""
        for (x,y) in itertools.combinations(np.arange(self.nVibs),2):
                #print Eq2d[x,y]*au2wn , magMu2d[x,y],'combination bands' , x,y
                comboFile2.write(str( Eq2d[x,y]*au2wn)+"   "+str(magMu2d[x,y])+"       "+str(x)+" "+str(y)+"\n")

        for i in range(self.nVibs):
            print Eq[i]*au2wn, magAvgMu[i], 'mode ',i
            #fundamentalFile.write(str(noKE_funds[i]*au2wn)+"   "+str(magAvgMu[i])+"       "+str(i)+"\n")
        for i in range(self.nVibs):
            for j in range(i):
                print Eq2d[i,j]*au2wn , magMu2d[i,j],'combination bands' , i,j
                comboFile.write(str( Eq2d[i,j]*au2wn)+"   "+str(magMu2d[i,j])+"       "+str(i)+" "+str(j)+"\n")
                #justVComboFile.write(str(noKE_combos[i,j]*au2wn)+"   "+str(magMu2d[i,j])+"       "+str(i)+" "+str(j)+"\n")
        for i in range(self.nVibs):
            print Eq2d[i,i]*au2wn , magMu2d[i,i],'overtone bands' , i,i
            comboFile.write(str( Eq2d[i,i]*au2wn)+"   "+str(magMu2d[i,i])+"       "+str(i)+" "+str(i)+"\n")
            comboFile2.write(str( Eq2d[i,i]*au2wn)+"   "+str(magMu2d[i,i])+"       "+str(i)+" "+str(i)+"\n")

        
        #np.savetxt("dgnl2",dgnl2)
        #fundamentalFile.close()
        comboFile.close()
        #justVComboFile.close()
        return Eq*au2wn,magAvgMu, Eq2d*au2wn,magMu2d


    def calculatePotentialEnergy(self,coords,pe):
        equilibriumEnergy=self.wfn.molecule.getEquilibriumEnergy()
        if self.wfn.molecule.name in ProtonatedWaterTrimer:
            electronicEnergy = pe
        elif self.wfn.molecule.name in ProtonatedWaterTetramer:
            electronicEnergy = pe
        else:
            electronicEnergy=self.wfn.molecule.V(coords)
        relativePotentialEnergy=electronicEnergy-equilibriumEnergy
        #print 'average relative potential energy', np.average(relativePotentialEnergy)
        #print 'descendant weighted average relative potential energy', np.average(relativePotentialEnergy,weights=dw)
        return relativePotentialEnergy

    def calculateQCoordinates(self,moments, dw,gmf,setOfWalkers):
        #def calculateQCoordinates(self,moments,dw,gmf,setOfWalkers):
        #gmf = gmatrix
        print 'calculating Normal coordinates'
        walkerSize=len(dw)
        #dwChunks = np.array_split(dw,100)
        mu2AveR = np.zeros((self.nVibs,self.nVibs))
        sh = np.memmap('smap'+setOfWalkers, dtype='float64', mode='r', shape=(int(walkerSize),int(self.nVibs),int(self.nVibs)))
        dh = np.memmap('dmap'+setOfWalkers, dtype='float64', mode='r', shape=int(walkerSize))
        if walkerSize > 1000000:
            chunkSize=1000000
        else:
            chunkSize=10
        cycle = np.arange(0,walkerSize,chunkSize)
        last=False

        for j in cycle:
            k = j+chunkSize
            if k > walkerSize-chunkSize:
                last = True
            if not last:
                mu2AveR += np.sum(sh[j:k]*dh[j:k,np.newaxis,np.newaxis],axis=0)
            else:
                mu2AveR += np.sum(sh[j:]*dh[j:,np.newaxis,np.newaxis],axis=0)
        mu2Ave = np.divide(mu2AveR,np.sum(dw))/2.00000 #commented this to see what would happen

        GHalfInv=self.diagonalizeRootG(self.G)
        mu2AvePrime=np.dot(GHalfInv,np.dot(mu2Ave,GHalfInv)) # mass weights g^-1/2 . sm . g^-1/2
        eigval,vects=np.linalg.eigh(mu2AvePrime)
        eigvalt, vectt = sla.eigh(mu2Ave,self.G)
        print 'test'
        """testVect = np.dot(self.G,vects)
        testest = np.dot(np.dot(vects.conj(),self.G),vects)
        testest2 = np.dot(np.dot(vects, mu2Ave), vects)

        s1=np.sum(np.square(vects1),axis=1)
        s2=np.sum(np.square(vects),axis=1)
        vects3=vects/np.linalg.norm(vects,axis=1)[:,np.newaxis]
        s3 = np.sum(np.square(vects3),axis=1)"""

        print 'diagonalized <mu^2>'
        #for i in range(self.wfn.molecule.nVibs):
        #    print 'v[',i,',]:',eigval[i]
        #    print vects[:,i]

        #GAAH                                                              
        TransformationMatrix=np.dot(vects.transpose(),GHalfInv)
        #print 'RESULTS'
        Tnorm=1.0*TransformationMatrix # NEED TO DEEP COPY :-0
        alpha=1.0*eigval #AS in alpha_j in equation 5 of the JPC A 2011 h5o2 dier paper                                          
        #save the transformation matrix for future reference                                                                      
        TMatFileName='TransformationMatrix'+setOfWalkers+'.data'
        #stop
        #TMatFileName = 'allHTesting/spectra/TransformationMatrix.data'
        np.savetxt(TMatFileName,TransformationMatrix)
        gmf = gmf[30:-5]
        print 'assignment file name', setOfWalkers+gmf
        if 'Eck' in gmf:
            gmf=setOfWalkers
        assignF = open(self.path+'assignments_'+setOfWalkers+gmf,'w+')

        for i,(vec,q2) in enumerate(zip(TransformationMatrix,eigval)):
            if verbose: print '\n',i,':<q^2 >=',q2
            #        alpha[i]=alpha[i]/(firstterm-(alpha[i]*alpha[i]))                                                            
            if verbose: print 'vec    ',vec
            Tnorm[i]=np.abs(vec)/np.max(np.abs(vec))
            sortvecidx=np.argsort(abs(vec))[::-1]
            #print 'sortvecidx: '
            sortedvec=vec[sortvecidx]
            sortedNames=use.sortList(abs(vec),self.wfn.molecule.internalName)[::-1]
            #sortedvecLocalVersion=use.sortList(abs(vec),vec)[::-1]
            #print 'sorted\n',zip(sortvecidx,sortedvec,sortedNames,sortedvecLocalVersion)
            print 'assignments\n',zip(sortedNames,sortvecidx,sortedvec)[0:4]
            for hu in range(self.nVibs):
                assignF.write("%s %d %5.12f " % (sortedNames[hu],sortvecidx[hu],sortedvec[hu]))
            assignF.write('\n \n')
        assignF.close()


            #calculate q from the moments and the transformation matrix
        q=[]
        #print moments.shape
        for s in moments:
            q.append(np.dot(TransformationMatrix,s))

        q=np.array(q)
        q2=q**2
        #q4=q**4

        return q,q2 #,q4
