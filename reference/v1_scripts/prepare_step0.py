import os, sys

dataset = sys.argv[1]

if not os.path.exists('ECOD_length'):
    os.system('cp /data/data1/conglab/qcong/for/domain_parser/for_dustin/ECOD_length ./')
if not os.path.exists('ECOD_pdbmap'):
    os.system('cp /data/data1/conglab/qcong/for/domain_parser/for_dustin/ECOD_pdbmap ./')
if not os.path.exists('ECOD_norms'):
    os.system('cp /data/data1/conglab/qcong/for/domain_parser/for_dustin/ECOD_norms ./')
if not os.path.exists('ecod.latest.domains'):
    os.system('cp /data/data1/conglab/qcong/for/domain_parser/for_dustin/ecod.latest.domains ./')
if not os.path.exists('domass_epo29.data-00000-of-00001'):
    os.system('cp /data/data1/conglab/qcong/for/domain_parser/for_dustin/domass_epo29.data-00000-of-00001 ./')
if not os.path.exists('domass_epo29.index'):
    os.system('cp /data/data1/conglab/qcong/for/domain_parser/for_dustin/domass_epo29.index ./')
if not os.path.exists('domass_epo29.meta'):
    os.system('cp /data/data1/conglab/qcong/for/domain_parser/for_dustin/domass_epo29.meta ./')
if not os.path.exists('tgroup_length'):
    os.system('cp /data/data1/conglab/qcong/for/domain_parser/for_dustin/tgroup_length ./')
if not os.path.exists('ECOD_maps'):
    os.system('ln -s /data/data1/conglab/qcong/for/domain_parser/for_dustin/ECOD_maps ./')
if not os.path.exists('ECOD_pdbs'):
    os.system('ln -s /data/data1/conglab/qcong/for/domain_parser/for_dustin/ECOD_pdbs ./')
if not os.path.exists('posi_weights'):
    os.system('ln -s /data/data1/conglab/qcong/for/domain_parser/for_dustin/posi_weights ./')
if not os.path.exists('ecod_internal'):
    os.system('ln -s /data/data1/conglab/qcong/for/domain_parser/for_dustin/ecod_internal ./')

os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/batch_run.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step0.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step1.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step2.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step3.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step4.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step5.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step6.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step7.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step8.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step9.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step10.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step11.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step12.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step13.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step14.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step15.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step16.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step17.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step18.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step19.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step21.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/prepare_step23.py ./')

os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step1_get_AFDB_seqs.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step2_get_AFDB_pdbs.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step3_run_hhsearch.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step4_run_foldseek.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step5_process_hhsearch.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step6_process_foldseek.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step7_prepare_dali.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step8_iterative_dali.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step9_analyze_dali.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step10_get_support.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step11_get_good_domains.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step12_get_sse.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step13_get_diso.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step14_parse_domains.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step15_prepare_domass.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step16_run_domass.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step17_get_confident.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step18_get_mapping.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step19_get_merge_candidates.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step20_extract_domains.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step21_compare_domains.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step22_merge_domains.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step23_get_predictions.py ./')
os.system('cp /data/data1/conglab/qcong/for/domain_parser/dpam_automatic/step24_integrate_results.py ./')

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
        print ('There are ' + str(len(cif_cases)) + ' proteins to be classified from ' + dataset)
    else:
        print ('The number of cif (V4) files does not match the number of json (V4) files for ' + dataset + ', please check!')
else:
    print ('There is no directory for ' + dataset)

