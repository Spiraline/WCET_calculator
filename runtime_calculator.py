import csv
import argparse
import os

start_t = []
end_t = []
actual_runtime = {}
idx = 0

task_dic = {} 
acc_runtime = {}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', '-f', help='file path', required=True)
    parser.add_argument('--index', '-i', type=int, nargs='+', help='valid index for pid', required=True)
    parser.add_argument('--deli', '-d', help='csv file delimiter', default=',')
    parser.add_argument('--task', '-ts', help='task name', default='ndt_matching_pa')
    parser.add_argument('--tmp', '-tp', action='store_true', help='If you have tmp.txt, enable it', default=False)
    args = parser.parse_args()

    callback_file_path = args.file + ".csv"
    if not os.path.exists(callback_file_path):
        print("File not exists : %s" % (callback_file_path))
        exit(1)

    trace_file_path = args.file + ".dat"
    if not os.path.exists(trace_file_path):
        print("File not exists : %s" % (trace_file_path))
        exit(1)

    if trace_file_path.split(".") == 1 or trace_file_path.split(".")[-1] != 'dat':
        print("trace file should be dat file!")
        exit(1)

    if not args.tmp:
        report_cmd = 'trace-cmd report ' + trace_file_path + ' > tmp.txt'
        os.system(report_cmd)
        print("[System] trace-cmd for dat file Complete")
    elif not os.path.exists('tmp.txt'):
        print("You should have tmp.txt or disable --tmp option")
        exit(1)
    else:
        print("[System] You already have tmp.txt")

    # Parse Data
    with open(callback_file_path, 'r') as f:
        reader = csv.reader(f, delimiter=args.deli)
        for line in reader:
            start_t.append(float(line[2]))
            end_t.append(float(line[2]) + (float(line[1]) - float(line[0])))

    print("[System] Parse csv file Complete")

    pid_list = []

    # # Check every pid for given task name
    with open('tmp.txt', 'r') as f:
        f.readline()
        for line in f.readlines():
            taskname = line.split(']')[0].split('-')[0].split()[-1]
            pid = line.split(']')[0].split('-')[-1].split()[0]
            if taskname == args.task and pid not in pid_list:
                pid_list.append(pid)

    pid_list = sorted(pid_list, key = lambda x : int(x))

    print("[System] %d pid found for %s node ( " % (len(pid_list), args.task), end="")
    for pid in pid_list:
        print(pid, end=" ")
    print(")")

    for i in args.index:
        if i > len(pid_list):
            os.remove('tmp.txt')
            print("[System] Invalid index. There are %d pid ( " % len(pid_list), end="")
            for pid in pid_list:
                print(pid, end=" ")
            print(") only.")
            exit(1)
        task_dic[pid_list[i]] = {"slice_start_t" : 0, "isRun" : False}
        actual_runtime[pid_list[i]] = []
        acc_runtime[pid_list[i]] = 0

    with open('tmp.txt', 'r') as f:
        # for cpu number line
        f.readline()
        f.readline()
        for line in f.readlines():
            ts = float(line.split(': ')[0].split()[-1])
            task = line.split(': ')[1]

            if ts > end_t[idx]:
                for pid in task_dic:
                    # if task was running, add remaining execution time
                    if task_dic[pid]["isRun"]:
                        acc_runtime[pid] = acc_runtime[pid] + (end_t[idx] - task_dic[pid]["slice_start_t"])
                    task_dic[pid]["slice_start_t"] = 0
                    task_dic[pid]["isRun"] = False
                    actual_runtime[pid].append(acc_runtime[pid])
                    acc_runtime[pid] = 0
                idx = idx+1
                if idx >= len(end_t):
                    break

            if task == 'sched_switch' and ts > start_t[idx]:
                src_task = line.split(' ==> ')[0].split(' [')[-2].split()[-1].split(':')[0]
                src_pid = line.split(' ==> ')[0].split(' [')[-2].split()[-1].split(':')[-1]
                dst_task = line.split(' ==> ')[1].split(':')[0]
                dst_pid = line.split(' ==> ')[1].split(':')[-1].split()[0]

                if dst_task == args.task and dst_pid in task_dic:
                    task_dic[dst_pid]["slice_start_t"] = ts
                    task_dic[dst_pid]["isRun"] = True
                if src_task == args.task and src_pid in task_dic:
                    # not start case
                    if task_dic[src_pid]["slice_start_t"] != 0:
                        acc_runtime[src_pid] = acc_runtime[src_pid] + (ts - task_dic[src_pid]["slice_start_t"])
                        task_dic[src_pid]["isRun"] = False
                    # start case
                    else:
                        acc_runtime[src_pid] = acc_runtime[src_pid] + (ts - start_t[idx])

    print("[System] Parse dat file Complete")

    # idx = len(actual_runtime)-1

    # print(actual_runtime)

    idx = 0
    # while actual_runtime[idx] <= 0:
    #     idx = idx+1

    os.remove('tmp.txt')

    for pid in actual_runtime.keys():

        output_file_path = args.file.split('/')[-1] + "_res_" + str(pid) + ".csv"

        with open(output_file_path, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            # Omit First data
            for i in range(idx+1, len(actual_runtime[pid])):
                writer.writerow([start_t[i], end_t[i], round(actual_runtime[pid][i], 6)])
    
    print("[System] Output Completely Generated!")
