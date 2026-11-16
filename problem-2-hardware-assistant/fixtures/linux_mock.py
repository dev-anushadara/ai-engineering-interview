"""
Realistic Linux Laptop Hardware Fixtures (e.g., ThinkPad / Dell Developer Edition)
Used when running with --mock flag or on non-Linux platforms for testing.
"""

LSCPU_JSON = """{
   "lscpu": [
      {"field": "Architecture:", "data": "x86_64"},
      {"field": "CPU op-mode(s):", "data": "32-bit, 64-bit"},
      {"field": "Address sizes:", "data": "39 bits physical, 48 bits virtual"},
      {"field": "Byte Order:", "data": "Little Endian"},
      {"field": "CPU(s):", "data": "16"},
      {"field": "On-line CPU(s) list:", "data": "0-15"},
      {"field": "Vendor ID:", "data": "GenuineIntel"},
      {"field": "Model name:", "data": "12th Gen Intel(R) Core(TM) i7-1260P"},
      {"field": "CPU family:", "data": "6"},
      {"field": "Model:", "data": "154"},
      {"field": "Thread(s) per core:", "data": "2"},
      {"field": "Core(s) per socket:", "data": "12"},
      {"field": "Socket(s):", "data": "1"},
      {"field": "CPU max MHz:", "data": "4700.0000"},
      {"field": "CPU min MHz:", "data": "400.0000"},
      {"field": "L1d cache:", "data": "384 KiB (12 instances)"},
      {"field": "L1i cache:", "data": "512 KiB (12 instances)"},
      {"field": "L2 cache:", "data": "9 MiB (3 instances)"},
      {"field": "L3 cache:", "data": "18 MiB (1 instance)"},
      {"field": "Virtualization:", "data": "VT-x"}
   ]
}"""

LSBLK_JSON = """{
   "blockdevices": [
      {
         "name": "nvme0n1",
         "size": "1000204886016",
         "type": "disk",
         "tran": "nvme",
         "mountpoints": [null],
         "model": "Samsung SSD 980 PRO 1TB",
         "children": [
            {
               "name": "nvme0n1p1",
               "size": "536870912",
               "type": "part",
               "tran": null,
               "mountpoints": ["/boot/efi"],
               "model": null
            },
            {
               "name": "nvme0n1p2",
               "size": "1073741824",
               "type": "part",
               "tran": null,
               "mountpoints": ["/boot"],
               "model": null
            },
            {
               "name": "nvme0n1p3",
               "size": "998592184320",
               "type": "part",
               "tran": null,
               "mountpoints": ["/"],
               "model": null
            }
         ]
      }
   ]
}"""

FREE_OUTPUT = """               total        used        free      shared  buff/cache   available
Mem:        16558480     4251216     8921432      412892     3385832    11894372
Swap:        8388604           0     8388604
"""

PROC_MEMINFO = """MemTotal:       16558480 kB
MemFree:         8921432 kB
MemAvailable:   11894372 kB
Buffers:          341200 kB
Cached:          3044632 kB
SwapCached:            0 kB
Active:          4210400 kB
Inactive:        2891240 kB
SwapTotal:       8388604 kB
SwapFree:        8388604 kB
"""

LSPCI_OUTPUT = """00:00.0 Host bridge: Intel Corporation 12th Gen Core Processor Host Bridge/DRAM Registers (rev 02)
00:02.0 VGA compatible controller: Intel Corporation Alder Lake-P Integrated Graphics Controller (rev 0c)
	Subsystem: Lenovo ThinkPad X1 Carbon Gen 10
	Kernel driver in use: i915
	Kernel modules: i915
01:00.0 3D controller: NVIDIA Corporation GA107M [GeForce RTX 3050 Mobile] (rev a1)
	Subsystem: Lenovo Device 22eb
	Kernel driver in use: nvidia
	Kernel modules: nouveau, nvidia_drm, nvidia
00:14.0 USB controller: Intel Corporation Alder Lake PCH USB 3.2 xHCI Host Controller (rev 01)
00:1d.0 PCI bridge: Intel Corporation Alder Lake PCI Express Root Port #9 (rev 01)
02:00.0 Network controller: Intel Corporation Wi-Fi 6 AX211 (rev 20)
03:00.0 Non-Volatile memory controller: Samsung Electronics Co Ltd NVMe SSD Controller PM9A1/980
"""

DMIDECODE_MEMORY = """# dmidecode 3.4
Getting SMBIOS data from sysfs.
SMBIOS 3.4.0 present.

Handle 0x0010, DMI type 16, 23 bytes
Physical Memory Array
	Location: System Board
	Use: System Memory
	Error Correction Type: None
	Maximum Capacity: 64 GB
	Error Information Handle: Not Provided
	Number Of Devices: 2

Handle 0x0011, DMI type 17, 92 bytes
Memory Device
	Array Handle: 0x0010
	Error Information Handle: Not Provided
	Total Width: 64 bits
	Data Width: 64 bits
	Size: 16 GB
	Form Factor: SODIMM
	Set: None
	Locator: Controller0-ChannelA-DIMM0
	Bank Locator: BANK 0
	Type: DDR5
	Type Detail: Synchronous Unbuffered (Unregistered)
	Speed: 4800 MT/s
	Manufacturer: Micron Technology
	Serial Number: 2A3B4C5D
	Asset Tag: Not Specified
	Part Number: MTC8C1084S1SC48BA1
	Rank: 1
	Configured Memory Speed: 4800 MT/s
	Minimum Voltage: 1.1 V
	Maximum Voltage: 1.1 V
	Configured Voltage: 1.1 V

Handle 0x0012, DMI type 17, 92 bytes
Memory Device
	Array Handle: 0x0010
	Error Information Handle: Not Provided
	Total Width: Unknown
	Data Width: Unknown
	Size: No Module Installed
	Form Factor: SODIMM
	Set: None
	Locator: Controller0-ChannelB-DIMM0
	Bank Locator: BANK 1
	Type: Unknown
	Type Detail: None
	Speed: Unknown
	Manufacturer: Not Specified
	Serial Number: Not Specified
	Asset Tag: Not Specified
	Part Number: Not Specified
	Rank: Unknown
	Configured Memory Speed: Unknown
	Minimum Voltage: Unknown
	Maximum Voltage: Unknown
	Configured Voltage: Unknown
"""

BATTERY_INFO = {
    "capacity": "88",
    "status": "Discharging",
    "energy_full": "57000000",
    "energy_full_design": "60000000",
    "energy_now": "50160000",
    "technology": "Li-poly",
    "manufacturer": "Celxpert",
    "model_name": "L21C4P71"
}

