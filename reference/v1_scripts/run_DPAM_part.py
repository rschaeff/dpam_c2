import os, sys, time

dataset = sys.argv[1]
joblimit = sys.argv[2]
steps = set(sys.argv[3].split(','))

if '0' in steps:
    fp = os.popen('python prepare_step0.py ' + dataset)
    isgood = 0
    for line in fp:
        words = line.split()
        if len(words) >= 5:
            if words[0] == 'There' and words[1] == 'are' and words[3] == 'proteins' and words[4] == 'to':
                isgood = 1
                break
    fp.close()

    if not isgood:
        sys.exit()


#STEP1
if '1' in steps:
    for i in range(5):
        os.system('python prepare_step1.py ' + dataset)
        jobid = ''
        if os.path.exists('step1_' + dataset + '.cmds') and os.path.exists('step1_' + dataset + '.job'):
            fp = os.popen('sbatch step1_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step1 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step1 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP2
if '2' in steps:
    for i in range(5):
        os.system('python prepare_step2.py ' + dataset)
        jobid = ''
        if os.path.exists('step2_' + dataset + '.cmds') and os.path.exists('step2_' + dataset + '.job'):
            fp = os.popen('sbatch step2_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step2 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step2 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP3
if '3' in steps:
    for i in range(5):
        os.system('python prepare_step3.py ' + dataset + ' ' + joblimit)
        jobids = []
        for j in range(int(joblimit)):
            if os.path.exists('step3_' + dataset + '_' + str(j) + '.cmds') and os.path.exists('step3_' + dataset + '_' + str(j) + '.job'):
                if i:
                    time.sleep(300)
                fp = os.popen('sbatch step3_' + dataset + '_' + str(j) + '.job')
                for line in fp:
                    words = line.split()
                    if len(words) >= 4:
                        jobids.append(words[3])
                        break
                fp.close()

        if jobids:
            while 1:
                running = 0
                time.sleep(300)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] in jobids:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step3 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step3 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP4
if '4' in steps:
    for i in range(5):
        os.system('python prepare_step4.py ' + dataset + ' ' + joblimit)
        jobids = []
        for j in range(int(joblimit)):
            if os.path.exists('step4_' + dataset + '_' + str(j) + '.job'):
                fp = os.popen('sbatch step4_' + dataset + '_' + str(j) + '.job')
                for line in fp:
                    words = line.split()
                    if len(words) >= 4:
                        jobids.append(words[3])
                        break
                fp.close()

        if jobids:
            while 1:
                running = 0
                time.sleep(60)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] in jobids:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step4 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step4 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP5
if '5' in steps:
    for i in range(5):
        os.system('python prepare_step5.py ' + dataset)
        jobid = ''
        if os.path.exists('step5_' + dataset + '.cmds') and os.path.exists('step5_' + dataset + '.job'):
            fp = os.popen('sbatch step5_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step5 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step5 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP6
if '6' in steps:
    for i in range(5):
        os.system('python prepare_step6.py ' + dataset)
        jobid = ''
        if os.path.exists('step6_' + dataset + '.cmds') and os.path.exists('step6_' + dataset + '.job'):
            fp = os.popen('sbatch step6_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step6 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step6 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP7
if '7' in steps:
    for i in range(5):
        os.system('python prepare_step7.py ' + dataset)
        jobid = ''
        if os.path.exists('step7_' + dataset + '.cmds') and os.path.exists('step7_' + dataset + '.job'):
            fp = os.popen('sbatch step7_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step7 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step7 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP8
if '8' in steps:
    for i in range(5):
        os.system('python prepare_step8.py ' + dataset + ' ' + joblimit)
        jobids = []
        for j in range(int(joblimit)):
            if os.path.exists('step8_' + dataset + '_' + str(j) + '.job'):
                fp = os.popen('sbatch step8_' + dataset + '_' + str(j) + '.job')
                for line in fp:
                    words = line.split()
                    if len(words) >= 4:
                        jobids.append(words[3])
                        break
                fp.close()

        if jobids:
            while 1:
                running = 0
                time.sleep(300)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] in jobids:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step8 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step8 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP9
if '9' in steps:
    for i in range(5):
        os.system('python prepare_step9.py ' + dataset)
        jobid = ''
        if os.path.exists('step9_' + dataset + '.cmds') and os.path.exists('step9_' + dataset + '.job'):
            fp = os.popen('sbatch step9_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step9 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step9 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP10
if '10' in steps:
    for i in range(5):
        os.system('python prepare_step10.py ' + dataset)
        jobid = ''
        if os.path.exists('step10_' + dataset + '.cmds') and os.path.exists('step10_' + dataset + '.job'):
            fp = os.popen('sbatch step10_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step10 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step10 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP11
if '11' in steps:
    for i in range(5):
        os.system('python prepare_step11.py ' + dataset)
        jobid = ''
        if os.path.exists('step11_' + dataset + '.cmds') and os.path.exists('step11_' + dataset + '.job'):
            fp = os.popen('sbatch step11_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step11 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step11 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP12
if '12' in steps:
    for i in range(5):
        os.system('python prepare_step12.py ' + dataset)
        jobid = ''
        if os.path.exists('step12_' + dataset + '.cmds') and os.path.exists('step12_' + dataset + '.job'):
            fp = os.popen('sbatch step12_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step12 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step12 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP13
if '13' in steps:
    for i in range(5):
        os.system('python prepare_step13.py ' + dataset)
        jobid = ''
        if os.path.exists('step13_' + dataset + '.cmds') and os.path.exists('step13_' + dataset + '.job'):
            fp = os.popen('sbatch step13_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step13 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step13 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP14
if '14' in steps:
    for i in range(5):
        os.system('python prepare_step14.py ' + dataset + ' ' + joblimit)
        jobids = []
        for j in range(int(joblimit)):
            if os.path.exists('step14_' + dataset + '_' + str(j) + '.cmds') and os.path.exists('step14_' + dataset + '_' + str(j) + '.job'):
                fp = os.popen('sbatch step14_' + dataset + '_' + str(j) + '.job')
                for line in fp:
                    words = line.split()
                    if len(words) >= 4:
                        jobids.append(words[3])
                        break
                fp.close()

        if jobids:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] in jobids:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step14 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step14 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP15
if '15' in steps:
    for i in range(5):
        os.system('python prepare_step15.py ' + dataset)
        jobid = ''
        if os.path.exists('step15_' + dataset + '.cmds') and os.path.exists('step15_' + dataset + '.job'):
            fp = os.popen('sbatch step15_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step15 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step15 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP16
if '16' in steps:
    for i in range(5):
        os.system('python prepare_step16.py ' + dataset)
        jobid = ''
        if os.path.exists('step16_' + dataset + '.job'):
            fp = os.popen('sbatch step16_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step16 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step16 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP17
if '17' in steps:
    for i in range(5):
        os.system('python prepare_step17.py ' + dataset)
        jobid = ''
        if os.path.exists('step17_' + dataset + '.cmds') and os.path.exists('step17_' + dataset + '.job'):
            fp = os.popen('sbatch step17_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step17 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step17 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP18
if '18' in steps:
    for i in range(5):
        os.system('python prepare_step18.py ' + dataset)
        jobid = ''
        if os.path.exists('step18_' + dataset + '.cmds') and os.path.exists('step18_' + dataset + '.job'):
            fp = os.popen('sbatch step18_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step18 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step18 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP19
if '19' in steps:
    for i in range(5):
        os.system('python prepare_step19.py ' + dataset)
        jobid = ''
        if os.path.exists('step19_' + dataset + '.cmds') and os.path.exists('step19_' + dataset + '.job'):
            fp = os.popen('sbatch step19_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step19 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step19 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP20
if '20' in steps:
    os.system('python step20_extract_domains.py ' + dataset)


#STEP21
if '21' in steps:
    for i in range(5):
        os.system('python prepare_step21.py ' + dataset)
        jobid = ''
        if os.path.exists('step21_' + dataset + '.job'):
            fp = os.popen('sbatch step21_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step21 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step21 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP22
if '22' in steps:
    os.system('python step22_merge_domains.py ' + dataset)


#STEP23
if '23' in steps:
    for i in range(5):
        os.system('python prepare_step23.py ' + dataset)
        jobid = ''
        if os.path.exists('step23_' + dataset + '.cmds') and os.path.exists('step23_' + dataset + '.job'):
            fp = os.popen('sbatch step23_' + dataset + '.job')
            for line in fp:
                words = line.split()
                if len(words) >= 4:
                    jobid = words[3]
                    break
            fp.close()

        if jobid:
            while 1:
                running = 0
                time.sleep(10)
                fp = os.popen('squeue')
                for line in fp:
                    words = line.split()
                    if words[0] == jobid:
                        running = 1
                fp.close()
                if not running:
                    break
        else:
            print ('step23 for ' + dataset + ' is fully finished')
            break
    else:
        print ('step23 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
        sys.exit()


#STEP24
if '24' in steps:
    os.system('python step24_integrate_results.py ' + dataset)
