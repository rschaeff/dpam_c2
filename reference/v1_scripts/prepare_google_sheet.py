import os, sys
import numpy as np

fp = open('ecod.latest.domains','r')
ecod2keyword = {}
ecod2arch = {}
ecod2xname = {}
ecod2hname = {}
ecod2tname = {}
for line in fp:
    if line[0] != '#':
        words = line[:-1].split('\t')
        ecod = words[0]
        ecod2keyword[ecod] = words[1]
        ecod2arch[ecod] = words[9]
        xname = words[10][1:-1]
        hname = words[11][1:-1]
        tname = words[12][1:-1]
        ecod2tname[ecod] = tname
        if hname == 'NO_H_NAME':
            ecod2hname[ecod] = tname
        else:
            ecod2hname[ecod] = hname
        if xname == 'NO_X_NAME':
            if hname == 'NO_H_NAME':
                ecod2xname[ecod] = tname
            else:
                ecod2xname[ecod] = hname
        else:
            ecod2xname[ecod] = xname
fp.close()


fp = open('staa8_domains','r')
good_prots = set([])
prot2domains = {}
for countl, line in enumerate(fp):
    if countl:
        words = line.split()
        prot = words[0]
        name = words[1]
        domrange = words[2]
        domsize = 0
        for seg in domrange.split(','):
            if '-' in seg:
                start = int(seg.split('-')[0])
                end = int(seg.split('-')[1])
                domsize += end - start + 1
            else:
                domsize += 1
        ecod = words[3]
        ecodkey = words[4]
        tgroup = words[5]
        DPAMprob = words[6]
        HHprob = words[7]
        hitcov = words[8]
        groupcov = words[9]
        judge = words[10]
        Hcount = words[11]
        Scount = words[12]
        try:
            prot2domains[prot].append([name, domrange, str(domsize), ecod, ecodkey, tgroup, DPAMprob, HHprob, hitcov, groupcov, judge, Hcount, Scount])
        except KeyError:
            good_prots.add(prot)
            prot2domains[prot] = [[name, domrange, str(domsize), ecod, ecodkey, tgroup, DPAMprob, HHprob, hitcov, groupcov, judge, Hcount, Scount]]
fp.close()


fp = open('staa8_func','r')
prots = []
prot2length = {}
prot2func = {}
for countl, line in enumerate(fp):
    if countl:
        words = line[:-1].split('\t')
        prot = words[0]
        prots.append(prot)
        prot2length[prot] = words[1]
        prot2func[prot] = words[2]
fp.close()


rp = open('staa8_ECOD.tsv','w')
rp.write('Uniprot\tProtein Name\tLength\tDomain\tRange\tSize\tHelix\tStrand\tECOD ref\tPDB\tT-group\tDPAM prob\tHH prob\tHit cov\tGroup cov\tQC class\tArch name\tXgrp name\tHgrp name\tTgrp name\n')

for prot in prots:
    length = str(prot2length[prot])
    protname = prot2func[prot]
    newline = ''

    if prot in good_prots:
        for item in prot2domains[prot]:
            domname = item[0]
            domrange = item[1]
            domsize = item[2]
            Hcount = item[11]
            Scount = item[12]
            newline = '=HYPERLINK(\"https://alphafold.ebi.ac.uk/entry/' + prot + '\",\"' + prot + '\")\t=HYPERLINK(\"https://www.uniprot.org/uniprot/' + prot + '\",\"' + protname + '\")\t'
            newline += length + '\t' + domname + '\t' + domrange + '\t' + domsize + '\t' + Hcount + '\t' + Scount + '\t'
            ecodnum = item[3]
            if ecodnum != 'na':
                judge = item[10]
                if judge == 'good_domain':
                    Aname = ecod2arch[ecodnum]
                    Xname = ecod2xname[ecodnum]
                    Hname = ecod2hname[ecodnum]
                    Tname = ecod2tname[ecodnum]
                else:
                    Aname = judge
                    Xname = judge
                    Hname = judge
                    Tname = judge

                ecodkey = item[4]
                pdbid = ecodkey[1:5].upper()
                tgroup = item[5]
                DPAMprob = item[6]
                HHprob = item[7]
                hitcov = item[8]
                groupcov = item[9]
                newline += '=HYPERLINK(\"http://prodata.swmed.edu/ecod/complete/domain/' + ecodkey + '\",\"' + ecodkey + '\")\t=HYPERLINK(\"https://www.rcsb.org/structure/' + pdbid + '\",\"' + pdbid + '\")\t'
                newline += '=HYPERLINK(\"http://prodata.swmed.edu/ecod/complete/tree?id=' + tgroup + '\",\"' + tgroup + '\")\t' + DPAMprob + '\t' + HHprob + '\t' + hitcov + '\t' + groupcov + '\t'
                newline += judge + '\t' + Aname + '\t' + Xname + '\t' + Hname + '\t' + Tname + '\n'
                rp.write(newline)
            else:
                newline += 'na\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\n'
                rp.write(newline)
    else:
        newline = '=HYPERLINK(\"https://alphafold.ebi.ac.uk/entry/' + prot + '\",\"' + prot + '\")\t=HYPERLINK(\"https://www.uniprot.org/uniprot/' + prot + '\",\"' + protname + '\")\t' 
        newline += length + '\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\tna\n'
        rp.write(newline)
rp.close()
