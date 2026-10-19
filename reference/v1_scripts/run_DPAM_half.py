import os, sys, time

dataset = sys.argv[1]
joblimit = sys.argv[2]

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
            time.sleep(60)
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
            time.sleep(60)
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
for i in range(5):
    os.system('python prepare_step3.py ' + dataset + ' ' + joblimit)
    jobids = []
    for j in range(int(joblimit)):
        if os.path.exists('step3_' + dataset + '_' + str(j) + '.cmds') and os.path.exists('step3_' + dataset + '_' + str(j) + '.job'):
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
    time.sleep(1800)
else:
    print ('step3 for ' + dataset + ' cannot be finished after 5 attemps, please contact Qian for trouble shooting')
    sys.exit()


#STEP4
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
            time.sleep(60)
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
            time.sleep(60)
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
            time.sleep(60)
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
