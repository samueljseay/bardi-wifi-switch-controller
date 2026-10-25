# License and provenance

Project-owned Python code, tests, and documentation are licensed under
Apache-2.0. See [LICENSE](LICENSE). This grant does not cover unrelated research
inputs or trademarks. This is an independent project, not a Bardi or Tuya product.

The runtime installs TinyTuya 1.20.0 as a separate dependency. It uses TinyTuya's
LAN session and packet implementation, with a receive subclass that rejects
failed protocol-3.4 response HMACs. No TinyTuya distribution is bundled here.
Upstream: https://github.com/jasonacox/tinytuya.

TinyTuya's installed package carries the following MIT license:

```text
MIT License

Copyright (c) 2024 Jason Cox

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The controller was developed using public library and SDK references, synthetic
packet tests, an owner-authorized offline app-cache inspection, and observed
device responses. It makes no clean-room claim. Android app binaries, extracted
proprietary code, vendor libraries, firmware, emulator tooling, and real device
data are excluded. The documented app methods describe the observed interface;
no app implementation is distributed.
