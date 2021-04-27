import csv
import argparse
import os
import copy

actual_runtime = []
idx = 0
name_matching_dic = {}
callback_info = []
pid_exec_info = {}

# acc_runtime by node
acc_runtime = {}

# exec info by pid
proc_exec_info = {}

curr_cpu = -1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--node', '-n', help='node name', required=True)
    parser.add_argument('--prof', '-p', help='.dat file', default='tmp.dat')
    parser.add_argument('--deli', '-d', help='csv file delimiter', default=',')
    parser.add_argument('--tmp', '-t', action='store_true', help='If you have tmp.txt, enable it', default=False)
    args = parser.parse_args()

    task_execution_file_path = os.getcwd() + '/' + args.node + '.csv'
    if not os.path.exists(task_execution_file_path):
        print("csv file not exists : %s" % (task_execution_file_path))
        exit(1)

    if not args.tmp and not os.path.exists(args.prof):
        print("Profiling file not exists : %s" % (args.prof))
        exit(1)

    if args.prof.split(".") == 1 or args.prof.split(".")[-1] != 'dat':
        print("Profiling file should be dat file!")
        exit(1)

    if not args.tmp:
        report_cmd = 'trace-cmd report ' + args.prof + '| grep switch > tmp.txt'
        os.system(report_cmd)
        print("[System] trace-cmd for dat file Complete")
    elif not os.path.exists('tmp.txt'):
        print("You should have tmp.txt or disable --tmp option")
        exit(1)
    else:
        print("[System] You already have tmp.txt")

    ### Matching PID in csv and .txt file
    # Node name : name in csv
    # Process name : name in trace-cmd
    with open(task_execution_file_path, 'r') as f:
        reader = csv.reader(f, delimiter=args.deli)
        for line in reader:
            # Add callback info
            callback_info.append({"start_t" : float(line[0]), "end_t" : float(line[1]), "pid" : int(line[2])})

            # Add name_matching 
            pid = int(line[2])
            if pid not in name_matching_dic:
                name_matching_dic[pid] = {'node_name' : args.node}
    
    with open('tmp.txt', 'r') as f:
        for line in f.readlines():
            process_name = line.split(']')[0].split('-')[0].split()[-1]
            pid = int(line.split(']')[0].split('-')[-1].split()[0])
            if pid in name_matching_dic and 'process_name' not in name_matching_dic[pid]:
                name_matching_dic[pid]['process_name'] = process_name
            elif pid not in name_matching_dic:
                name_matching_dic[pid] = {'process_name' : process_name}
            if pid not in proc_exec_info:
                proc_exec_info[pid] = {'slice_start_t' : 0, 'isRun' : False}
            
            if process_name not in acc_runtime:
                acc_runtime[process_name] = 0
                
    print("[System] Name Matching between csv and trace-cmd result Complete")

    ### Parse trace-cmd result 
    with open('tmp.txt', 'r') as f:
        tracecmd_raw = f.readlines()
        line_num = len(tracecmd_raw)
        line_idx = 0
        prev_idx = 0

        for p_name in acc_runtime:
            acc_runtime[p_name] = 0

        while line_idx < line_num:
            running_pid = callback_info[idx]["pid"]
            line = tracecmd_raw[line_idx]
            ts = float(line.split(': ')[0].split()[-1]) / 1000000000
            src_pid = int(line.split(' ==> ')[0].split(' [')[-2].split()[-1].split(':')[-1])
            src_proc = line.split(' ==> ')[0].split(' [')[-2].split()[-1].split(':')[0]
            dst_pid = int(line.split(' ==> ')[1].split(':')[-1].split()[0])
            dst_proc = line.split(' ==> ')[1].split(':')[0]
            cpu = int(line.split('[')[1].split(']')[0])

            if dst_pid == running_pid or (src_pid == running_pid and proc_exec_info[src_pid]["slice_start_t"] == 0):
                if cpu != curr_cpu:
                    for pid in proc_exec_info:
                        if proc_exec_info[pid]["isRun"] and pid in name_matching_dic:
                            acc_runtime[name_matching_dic[pid]["process_name"]] += (callback_info[idx]['end_t'] - proc_exec_info[pid]["slice_start_t"])

                    for pid in proc_exec_info:
                        proc_exec_info[pid]["slice_start_t"] = 0
                        proc_exec_info[pid]["isRun"] = False
                    curr_cpu = cpu

            if ts > callback_info[idx]['end_t'] or line_idx == line_num - 1:
                # Add remain execution time if running
                for pid in proc_exec_info:
                    if proc_exec_info[pid]["isRun"] and pid in name_matching_dic:
                        acc_runtime[name_matching_dic[pid]["process_name"]] += (callback_info[idx]['end_t'] - proc_exec_info[pid]["slice_start_t"])
                for pid in proc_exec_info:
                    proc_exec_info[pid]["slice_start_t"] = 0
                    proc_exec_info[pid]["isRun"] = False

                actual_runtime.append(copy.deepcopy(acc_runtime))
                
                for p_name in acc_runtime:
                    acc_runtime[p_name] = 0

                idx = idx + 1
                curr_cpu = -1

                if idx >= len(callback_info) or line_idx == line_num - 1:
                    break

                # Resolve overlap issue
                if callback_info[idx]['start_t'] < callback_info[idx-1]['end_t']:
                    while True:
                        line_idx -= 1
                        tmp_line = tracecmd_raw[line_idx]
                        tmp_ts = float(tmp_line.split(': ')[0].split()[-1]) / 1000000000
                        if tmp_ts < callback_info[idx]['start_t'] or line_idx == 0:
                            break

            elif ts > callback_info[idx]['start_t'] and curr_cpu == cpu:
                if dst_pid in proc_exec_info:
                    proc_exec_info[dst_pid]["slice_start_t"] = ts
                    proc_exec_info[dst_pid]["isRun"] = True
                if src_pid in proc_exec_info:
                    # not start case
                    if proc_exec_info[src_pid]["slice_start_t"] != 0 and name_matching_dic[src_pid]["process_name"] in acc_runtime:
                        acc_runtime[name_matching_dic[src_pid]["process_name"]] += (ts - proc_exec_info[src_pid]["slice_start_t"])
                        proc_exec_info[src_pid]["isRun"] = False
                    # start case
                    elif src_pid in name_matching_dic:
                        acc_runtime[name_matching_dic[src_pid]["process_name"]] += (ts - callback_info[idx]['start_t'])

            line_idx += 1

    print("[System] Parse trace-cmd result file Complete")

    if not args.tmp:
        os.remove('tmp.txt')

    idx = 0
    output_file_path = os.getcwd() + '/' + args.node + "_res.csv"

    with open(output_file_path, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        first_row = ['start_t', 'end_t', 'pid', 'node_name', 'response_t']
        for key in actual_runtime[idx]:
            first_row.append(key)
        writer.writerow(first_row)

        while idx < len(callback_info):
            res_data = [callback_info[idx]['start_t'], callback_info[idx]['end_t'], callback_info[idx]['pid'],
                        name_matching_dic[callback_info[idx]['pid']]['node_name'],
                        callback_info[idx]['end_t'] - callback_info[idx]['start_t']]
            
            for proc_name in actual_runtime[idx]:
                res_data.append(actual_runtime[idx][proc_name])

            writer.writerow(res_data)

            idx += 1

    print("[System] Output Completely Generated!")
