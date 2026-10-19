import os, sys

dataset = sys.argv[1]

check0 = 0
os.system('ulimit -s 100000')
if os.path.exists(dataset + '/'):
    fp = os.popen('ls -1 ' + dataset + '/AF-*-F1-model_v4.cif')
    rp = open(dataset + '_cif.list', 'w')
    cif_cases = []
    for line in fp:
        words = line[:-1].split('/')
        accession = words[1].split('-')[1]
        version = words[1].split('.')[0].split('_')[-1]
        rp.write(accession + '\t' + version + '\n')
        cif_cases.append([accession, version])
    fp.close()
    rp.close()

    fp = os.popen('ls -1 ' + dataset + '/AF-*-F1-predicted_aligned_error_v4.json')
    rp = open(dataset + '_json.list', 'w')
    json_cases = []
    for line in fp:
        words = line[:-1].split('/')
        accession = words[1].split('-')[1]
        version = words[1].split('.')[0].split('_')[-1]
        rp.write(accession + '\t' + version + '\n')
        json_cases.append([accession, version])
    fp.close()
    rp.close()

    if len(cif_cases) == len(json_cases):
        check0 = 1
        print ('There are ' + str(len(cif_cases)) + ' proteins to be classified from ' + dataset)
    else:
        print ('The number of cif (V4) files does not match the number of json (V4) files for ' + dataset + ', please check!')
else:
    print ('There is no directory for ' + dataset)



if check0:
    fp = open(dataset + '_cif.list', 'r')
    prots = []
    for line in fp:
        words = line.split()
        prots.append(words[0])
    fp.close()

    for prot in prots:
        check1 = 0
        if os.path.exists('step1/' + dataset + '/' + prot + '.fa'):
            fp = open('step1/' + dataset + '/' + prot + '.fa', 'r')
            check_header = 0
            check_seq = 0
            check_length = 0
            for line in fp:
                check_length += 1
                if line[0] == '>':
                    if line[1:-1] == prot:
                        check_header = 1
                else:
                    if len(line) > 10:
                        check_seq = 1
            fp.close()
            if check_header and check_seq and check_length == 2:
                check1 = 1


        check2 = 0
        fasta_length = 0
        if os.path.exists('step1/' + dataset + '/' + prot + '.fa'):
            fp = open('step1/' + dataset + '/' + prot + '.fa', 'r')
            for line in fp:
                if line[0] != '>':
                    fasta_length = len(line[:-1])
            fp.close()

        pdb_resids = set([])
        if os.path.exists('step2/' + dataset + '/' + prot + '.pdb'):
            fp = open('step2/' + dataset + '/' + prot + '.pdb', 'r')
            for line in fp:
                if len(line) >= 50:
                    if line[:4] == 'ATOM':
                        resid = int(line[22:26])
                        pdb_resids.add(resid)
            fp.close()
        pdb_length = len(pdb_resids)

        if fasta_length == pdb_length:
            if fasta_length:
                check2 = 1


        check3 = 0
        if os.path.exists('step3/' + dataset + '/' + prot + '.hmm') and os.path.exists('step3/' + dataset + '/' + prot + '.hhsearch'):
            fp = open('step3/' + dataset + '/' + prot + '.hmm', 'r')
            get_sspred = 0
            get_ssconf = 0
            for line in fp:
                if len(line) >= 10:
                    if line[0] == '>' and line[1:8] == 'ss_pred':
                        get_sspred = 1
                    elif line[0] == '>' and line[1:8] == 'ss_conf':
                        get_ssconf = 1
                if get_sspred and get_ssconf:
                    break
            fp.close()

            if get_sspred and get_ssconf:
                pass
            elif os.path.exists('step3/' + dataset + '/' + prot + '.a3m'):
                fp = open('step3/' + dataset + '/' + prot + '.a3m', 'r')
                count_line = 0
                for line in fp:
                    count_line += 1
                fp.close()
                if count_line == 2:
                    get_sspred = 1
                    get_ssconf = 1

            fp = open('step3/' + dataset + '/' + prot + '.hhsearch', 'r')
            start = 0
            end = 0
            hitsA = set([])
            hitsB = set([])
            for line in fp:
                words = line.split()
                if len(words) >= 2:
                    if words[0] == 'No' and words[1] == 'Hit':
                        start = 1
                    elif words[0] == 'No' and words[1] == '1':
                        hitsB.add(int(words[1]))
                        end = 1
                    elif start and not end:
                        hitsA.add(int(words[0]))
                    elif end:
                        if words[0] == 'No':
                            hitsB.add(int(words[1]))
            fp.close()
            last_words = line.split()

            if get_sspred and get_ssconf and hitsA == hitsB and not last_words:
                check3 = 1


        check4 = 0
        if os.path.exists('step4/' + dataset + '/' + prot + '.foldseek'):
            fp = open('step4/' + dataset + '/' + prot + '.foldseek','r')
            word_counts = set([])
            for line in fp:
                words = line.split()
                word_counts.add(len(words))
            fp.close()
            if len(word_counts) == 1 and 12 in word_counts:
                check4 = 1
        elif os.path.exists('step4/' + dataset + '/' + prot + '.done'):
            check4 = 1


        check5 = 0
        if os.path.exists('step5/' + dataset + '/' + prot + '.result'):
            fp = open('step5/' + dataset + '/' + prot + '.result','r')
            word_counts = set([])
            for line in fp:
                words = line.split()
                word_counts.add(len(words))
            fp.close()
            if len(word_counts) == 1 and 15 in word_counts:
                check5 = 1
        elif os.path.exists('step5/' + dataset + '/' + prot + '.done'):
            check5 = 1


        check6 = 0
        if os.path.exists('step6/' + dataset + '/' + prot + '.result'):
            fp = open('step6/' + dataset + '/' + prot + '.result','r')
            word_counts = set([])
            for line in fp:
                words = line.split()
                word_counts.add(len(words))
            fp.close()
            if len(word_counts) == 1 and 3 in word_counts:
                check6 = 1
        elif os.path.exists('step6/' + dataset + '/' + prot + '.done'):
            check6 = 1


        check7 = 0
        if os.path.exists('step7/' + dataset + '/' + prot + '_hits'):
            check7 = 1
        elif os.path.exists('step7/' + dataset + '/' + prot + '.done'):
            check7 = 1

    
        check8 = 0
        if os.path.exists('step8/' + dataset + '/' + prot + '_hits'):
            hit_count = 0
            fp = open('step8/' + dataset + '/' + prot + '_hits', 'r')
            hit_lines = []
            hit_line_count = 0
            bad = 0
            for line in fp:
                if line[0] == '>':
                    hit_count += 1
                    if hit_line_count:
                        if hit_line_count + 4 != len(hit_lines):
                            bad = 1
                            break
                    words = line.split()
                    hit_line_count = int(words[2])
                    hit_lines = []
                else:
                    hit_lines.append(line)
            fp.close()
            if hit_line_count:
                if hit_line_count + 4 != len(hit_lines):
                    bad = 1
            if not bad and hit_count:
                check8 = 1
        elif os.path.exists('step8/' + dataset + '/' + prot + '.done'):
            check8 = 1

    
        if check1:
            if os.path.exists('step1/' + dataset + '/' + prot + '.hhr'):
                os.system('rm step1/' + dataset + '/' + prot + '.hhr')
        else:
            if os.path.exists('step1/' + dataset + '/' + prot + '.fa'):
                os.system('rm step1/' + dataset + '/' + prot + '.fa')
            if os.path.exists('step1/' + dataset + '/' + prot + '.hhr'):
                os.system('rm step1/' + dataset + '/' + prot + '.hhr')
    
        if check2:
            pass
        else:
            if os.path.exists('step2/' + dataset + '/' + prot + '.pdb'):
                os.system('rm step2/' + dataset + '/' + prot + '.pdb')
    
        if check1 and check3:
            pass
        else:
            if os.path.exists('step3/' + dataset + '/' + prot + '.a3m'):
                os.system('rm step3/' + dataset + '/' + prot + '.a3m')
            if os.path.exists('step3/' + dataset + '/' + prot + '.hmm'):
                os.system('rm step3/' + dataset + '/' + prot + '.hmm')
            if os.path.exists('step3/' + dataset + '/' + prot + '.hhm'):
                os.system('rm step3/' + dataset + '/' + prot + '.hhm')
            if os.path.exists('step3/' + dataset + '/' + prot + '.hhsearch'):
                os.system('rm step3/' + dataset + '/' + prot + '.hhsearch')

        if check2 and check4:
            pass
        else:
            if os.path.exists('step4/' + dataset + '/' + prot + '.foldseek'):
                os.system('rm step4/' + dataset + '/' + prot + '.foldseek')

        if check1 and check3 and check5:
            pass
        else:
            if os.path.exists('step5/' + dataset + '/' + prot + '.result'):
                os.system('rm step5/' + dataset + '/' + prot + '.result')

        if check2 and check4 and check6:
            pass
        else:
            if os.path.exists('step6/' + dataset + '/' + prot + '.result'):
                os.system('rm step6/' + dataset + '/' + prot + '.result')

        if check1 and check2 and check3 and check4 and check5 and check6 and check7:
            pass
        else:
            if os.path.exists('step7/' + dataset + '/' + prot + '_hits'):
                os.system('rm step7/' + dataset + '/' + prot + '_hits')

        if check1 and check2 and check3 and check4 and check5 and check6 and check7 and check8:
            pass
        else:
            if os.path.exists('step8/' + dataset + '/' + prot + '_hits'):
                os.system('rm step8/' + dataset + '/' + prot + '_hits')

if os.path.exists('step9/' + dataset + '/'):
    os.system('rm -rf step9/' + dataset + '/')
if os.path.exists('step10/' + dataset + '/'):
    os.system('rm -rf step10/' + dataset + '/')
if os.path.exists('step11/' + dataset + '/'):
    os.system('rm -rf step11/' + dataset + '/')
if os.path.exists('step12/' + dataset + '/'):
    os.system('rm -rf step12/' + dataset + '/')
if os.path.exists('step13/' + dataset + '/'):
    os.system('rm -rf step13/' + dataset + '/')
if os.path.exists('step14/' + dataset + '/'):
    os.system('rm -rf step14/' + dataset + '/')
if os.path.exists('step15/' + dataset + '/'):
    os.system('rm -rf step15/' + dataset + '/')
if os.path.exists('step16/' + dataset + '/'):
    os.system('rm -rf step16/' + dataset + '/')
if os.path.exists('step17/' + dataset + '/'):
    os.system('rm -rf step17/' + dataset + '/')
if os.path.exists('step18/' + dataset + '/'):
    os.system('rm -rf step18/' + dataset + '/')
if os.path.exists('step19/' + dataset + '/'):
    os.system('rm -rf step19/' + dataset + '/')
if os.path.exists('step20/' + dataset + '/'):
    os.system('rm -rf step20/' + dataset + '/')
if os.path.exists('step23/' + dataset + '/'):
    os.system('rm -rf step23/' + dataset + '/')
if os.path.exists('step24/' + dataset + '/'):
    os.system('rm -rf step24/' + dataset + '/')
