import os, sys
import numpy as np

def get_domain_range(resids):
    segs = []
    resids.sort()
    for resid in resids:
        if not segs:
            segs.append([resid])
        else:
            if resid > segs[-1][-1] + 1:
                segs.append([resid])
            else:
                segs[-1].append(resid)
    seg_string = []
    for seg in segs:
        start = str(seg[0])
        end = str(seg[-1])
        seg_string.append(f'{start}-{end}')
    return ','.join(seg_string)

def get_resids(domain_range):
    domain_resids = set([])
    for seg in domain_range.split(','):
        if '-' in seg:
            start = int(seg.split('-')[0])
            end = int(seg.split('-')[1])
            for res in range(start, end + 1):
                domain_resids.add(res)
        else:
            domain_resids.add(int(seg))
    return domain_resids


fp = open('ECOD_length','r')
ecod2len = {}
for line in fp:
    words = line.split()
    ecod2len[words[0]] = int(words[2])
fp.close()

spname = sys.argv[1]
part = sys.argv[2]
fp = open('step16a_' + spname + '_' + part + '.list', 'r')
prots = []
for line in fp:
    words = line.split()
    prots.append(words[0])
fp.close()

for prot in prots:
    dpair2prob = {}
    get_dpairs = set([])
    if os.path.exists('step15a/' + spname + '/' + prot + '.data') and os.path.exists('step16/' + spname + '/' + prot + '.result'):
        fp = open('step16/' + spname + '/' + prot + '.result','r')
        for countl, line in enumerate(fp):
            if countl:
                words = line[:-1].split('\t')
                dpair = words[0] + '_' + words[3]
                try:
                    dpair2prob[dpair]
                    print ('error\t' + spname + '\t' + prot)
                except KeyError:
                    dpair2prob[dpair] = words[4]
                    get_dpairs.add(dpair)
        fp.close()

        fp = open('step15a/' + spname + '/' + prot + '.data', 'r')
        results = []
        results.append('Domain\tRange\tTgroup\tECOD_ref\tDPAM_prob\tHH_prob\tHH_cov\tHH_rank\tHH_ratio\tHH_Qcov\tHH_Hcov\tDALI_zscore\tDALI_qscore\tDALI_ztile\tDALI_qtile\tDALI_rank\tDALI_ratio\tDALI_Qcov\tDALI_Hcov\tConsensus_diff\tConsensus_cov\tHH_hit\tDALI_hit\tDALI_rot1\tDALI_rot2\tDALI_rot3\tDALI_trans\tHH_Qresids\tHH_Hresids\tDALI_Qresids\tDALI_Hresids\n')
        for countl, line in enumerate(fp):
            if countl:
                words = line[:-1].split('\t')
                ecodlen = ecod2len[words[3]]
                dpair = words[0] + '_' + words[3]
                judge1 = 0
                judge2 = 0

                if dpair in get_dpairs:
                    dpam_prob = dpair2prob[dpair]
                    DOMresids = get_resids(words[1])
                    if words[23] != 'na' and words[24] != 'na':
                        HQresids = get_resids(words[23])
                        HDresids = DOMresids.intersection(HQresids)
                        Hratio = str(round(len(HDresids) / len(HQresids), 2))
                        HQcov = str(round(len(HDresids) / len(DOMresids), 2))
                        HHcov = str(round(len(HDresids) / ecodlen, 2))
                        if float(Hratio) > 0.5:
                            judge1 = 1
                    else:
                        judge1 = 1
                        Hratio = 'na'
                        HQcov = 'na'
                        HHcov = 'na'

                    if words[25] != 'na' and words[26] != 'na':
                        DQresids = get_resids(words[25])
                        DDresids = DOMresids.intersection(DQresids)
                        Dratio = str(round(len(DDresids) / len(DQresids), 2))
                        DQcov = str(round(len(DDresids) / len(DQresids), 2))
                        DHcov = str(round(len(DDresids) / ecodlen, 2))
                        if float(Dratio) > 0.5:
                            judge2 = 1
                    else:
                        judge2 = 1
                        Dratio = 'na'
                        DQcov = 'na'
                        DHcov = 'na'
                    if judge1 and judge2:
                        results.append('\t'.join(words[:4]) + '\t' + dpam_prob + '\t' + '\t'.join(words[7:10]) + '\t' + Hratio + '\t' + HQcov + '\t' + HHcov + '\t' + '\t'.join(words[10:15]) + '\t' + Dratio + '\t' + DQcov + '\t' + DHcov + '\t' + '\t'.join(words[15:]) + '\n')
        fp.close()

        if len(results) > 1:
            rp = open('step16a/' + spname + '/' + prot + '.result','w')
            for line in results:
                rp.write(line)
            rp.close()
