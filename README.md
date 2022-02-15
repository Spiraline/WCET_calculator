# WCET Calculator

## Requirement

```
sudo apt-get install trace-cmd -y
```

* csv file which have (start_time, finish_time, pid) in each row
* trace-cmd dat file

## Argument
- `--node` (`-n`) : node name (same as csv file name)
- `--prof` (`-p`) : dat file path (default : `tmp.dat`)
- `--deli` (`-d`) : delimiter for csv file (default : `,`)
- `--tmp` (`-t`) : If you have trace-cmd report file, enable (default : `False`)

## Process
1. Run trace-cmd
  ```
  sudo trace-cmd record -e sched_switch -C mono -o tmp.dat
  ```
  You can see `Hit Ctrl^C to stop recording` message.
2. Run your task (ex : ROS, Autoware)
  Task should profile its (start_time, finish_time, pid)
  If your code is implemented by C/C++, you can insert below code
  ```
  struct timespec start_time, end_time;
  
  clock_gettime(CLOCK_MONOTONIC, &start_time);

  // some code you want to measure res_t, exec_t

  clock_gettime(CLOCK_MONOTONIC, &end_time);
  std::string print_file_path = std::getenv("HOME");
  print_file_path.append("/Documents/tmp/op_trajectory_evaluator.csv");
  FILE *fp;
  fp = fopen(print_file_path.c_str(), "a");
  fprintf(fp, "%lld.%.9ld,%lld.%.9ld,%d\n",start_time.tv_sec,start_time.tv_nsec,end_time.tv_sec,end_time.tv_nsec,getpid());
  fclose(fp);
  ```
3. Run my calculator
  ```
  python3 runtime_calculator.py -n $(node name) -p tmp.dat
  ```
  
## Example
![image](https://user-images.githubusercontent.com/44594966/116190103-fb52ae00-a764-11eb-828b-27440de32bf0.png)
