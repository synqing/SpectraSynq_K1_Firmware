"""Compile the actual diagnostic exporter/handler against a backpressured Print."""
import os
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT/'SPECTRASYNQ_K1_FIRMWARE/diag/k1_trace.h'
MENU = ROOT/'SPECTRASYNQ_K1_FIRMWARE/serial/serial_menu.cpp'


@pytest.fixture(scope='module')
def driver(tmp_path_factory):
    work = tmp_path_factory.mktemp('trace_transport')
    (work/'Arduino.h').write_text('''#pragma once
#include <cstdint>
inline uint32_t fake_now=0;
inline uint32_t millis(){return fake_now;}
inline void delay(uint32_t ms){fake_now+=ms;}
''')
    (work/'Print.h').write_text('''#pragma once
#include <cstddef>
#include <cstdint>
struct Print { virtual size_t write(const uint8_t*,size_t)=0; virtual ~Print()=default; };
''')
    (work/'mabutrace.h').write_text('''#pragma once
inline void get_json_trace_chunked(void* ctx,void(*emit)(void*,const char*,size_t)) {
 emit(ctx,"",0);
 emit(ctx,"{\\\"traceEvents\\\":[",16);
 emit(ctx,"{\\\"name\\\":\\\"probe\\\",\\\"ts\\\":1}",23);
 emit(ctx,"]}",2);
}
''')
    # Optional scratch copy enables an actual old-code red run, without editing firmware.
    header = Path(os.environ.get('K1_TRACE_TEST_HEADER', str(HEADER)))
    menu = Path(os.environ.get('K1_TRACE_TEST_MENU', str(MENU)))
    source = menu.read_text(); start=source.index('void cmd_trace_dump()'); end=source.index('\n}\n',start)+2
    cpp = work/'driver.cpp'
    cpp.write_text('''#include <algorithm>
#include <string>
#include <type_traits>
#include <cstdio>
#include <cstdlib>
#define FEATURE_MABUTRACE 1
#include <Arduino.h>
#include "'''+str(header)+'''"
struct FakePrint : Print {
 std::string bytes; int mode=0; unsigned calls=0;
 size_t write(const uint8_t* p,size_t n) override {
  ++calls;
  if(mode==3) return 0;
  if(mode==4) return n+1;
  if(mode==5 && calls>2) return 0;
  if(mode==2 && calls%3!=0) return 0;
  size_t k=mode==0?n:std::min(n,size_t(3));
  bytes.append(reinterpret_cast<const char*>(p),k);return k;
 }
 void println(const char* s="") { bytes+=s;bytes+='\\n'; }
} USBSerial;
template<class F> bool invoke(F f) {
 if constexpr(std::is_void_v<decltype(f())>) { f();return true; }
 else return f();
}
'''+source[start:end]+'''
int main(int argc,char** argv) {
 USBSerial.mode=std::atoi(argv[1]); fake_now=argc>3?0xfffffff0u:0u;
 uint32_t before=fake_now;
 if(argc>2 && std::string(argv[2])=="handler") cmd_trace_dump();
 else {
  bool ok=invoke([](){return k1_trace_dump_json(USBSerial);});
  std::printf("%d %u %u\\n",ok,uint32_t(fake_now-before),USBSerial.calls);
 }
 std::fwrite(USBSerial.bytes.data(),1,USBSerial.bytes.size(),stdout);
}
''')
    binary=work/'driver'
    subprocess.run(['c++','-std=c++17','-I',str(work),str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
    return binary


def run(driver, mode, handler=False, wrap=False):
    args=[str(driver),str(mode)]
    if handler or wrap: args.append('handler' if handler else 'dump')
    if wrap: args.append('wrap')
    return subprocess.run(args,check=True,capture_output=True,timeout=5).stdout


@pytest.mark.parametrize('mode',[0,1,2])
def test_success_is_exact_even_with_partial_and_zero_writes(driver,mode):
    status,body=run(driver,mode).split(b'\n',1)
    assert status.split()[0]==b'1'
    assert body==b'{"traceEvents":[{"name":"probe","ts":1}]}'


@pytest.mark.parametrize('mode',[3,4,5])
def test_failure_returns_false_and_never_says_done(driver,mode):
    status,body=run(driver,mode).split(b'\n',1)
    ok,elapsed,calls=map(int,status.split())
    assert ok==0
    if mode==4: assert calls==1 and elapsed==0
    else: assert elapsed==1000 and calls<=1003
    output=run(driver,mode,handler=True)
    assert b'[TRACE] Done.' not in output
    assert b'[TRACE] Export failed.' in output


def test_zero_progress_timeout_survives_clock_wrap(driver):
    status,_=run(driver,3,wrap=True).split(b'\n',1)
    assert list(map(int,status.split()))==[0,1000,1001]


def test_handler_reports_success_only_after_exact_json(driver):
    assert run(driver,1,handler=True)==(b'[TRACE] Flushing trace buffer...\n'
        b'{"traceEvents":[{"name":"probe","ts":1}]}\n[TRACE] Done.\n')
