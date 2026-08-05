# Flash and capture — Gate B spike

1. Close any serial monitor on `/dev/cu.usbmodem112401`.
2. `cd SpectraSynq_K1_Firmware && pio run -e k1_hardware_fft512_bench -t upload --upload-port /dev/cu.usbmodem112401`
3. `pio device monitor -b 115200 -p /dev/cu.usbmodem112401`
4. Send:
   - `:fft512_bench=live_hop,off`
   - `:fft512_bench=burst,1000`
   - `:fft512_bench=live_hop,on` (wait ~10 s ambient)
   - `:fft512_bench=report`
5. Save serial log to `fft_microbench_serial.log` and parse lines into `fft_microbench.json`.

Rollback: `pio run -e k1_hardware_stm -t upload --upload-port /dev/cu.usbmodem112401`
