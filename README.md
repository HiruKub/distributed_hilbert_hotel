# โครงงานโรงแรมอนันต์แบบกระจายด้วยเทคนิค Consistent Hashing
**Distributed Hilbert’s Hotel using Consistent Hashing**  
รายวิชา 01076109 Object Oriented Data Structures (ภาคเรียนที่ 1 ปีการศึกษา 2569)  
คณะวิศวกรรมศาสตร์ ภาควิชาวิศวกรรมคอมพิวเตอร์ สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง

---

## 1. ข้อมูลสมาชิกในกลุ่ม (กลุ่มที่ 2)
1. นายวิชาธร ขจรเนติกุล (รหัสนักศึกษา 68011025) - สัดส่วน 25%
2. นายศิวัช สูงสกุล (รหัสนักศึกษา 68011076) - สัดส่วน 25%
3. นางสาวศรัณย์พร หนองช้าง (รหัสนักศึกษา 68011812) - สัดส่วน 25%
4. นายอัษฎาวัชร สามสีเนียม (รหัสนักศึกษา 68011848) - สัดส่วน 25%

---

## 2. สภาพแวดล้อมและเวอร์ชันของภาษา (System Requirements)
* **ภาษาและตัวแปลภาษา:** Python 3.14 (CPython 64-bit) หรือ Python 3.10 ขึ้นไป
* **ไลบรารีมาตรฐานที่ใช้ (Standard Libraries):** `hashlib`, `bisect`, `math`, `enum`, `time`, `tracemalloc`, `unittest`
* **ไลบรารีภายนอก (External Libraries):** `matplotlib`, `pandas` (ใช้สำหรับงานสร้างกราฟและสรุปตารางการทดลอง)

### การติดตั้งแพ็กเกจที่จำเป็น
เปิด Terminal / Command Prompt ที่ระดับ Root Directory ของโปรเจกต์ แล้วเรียกใช้คำสั่ง:
```bash
pip install -r requirements.txt
```

---

## 3. วิธีการเรียกใช้งานโปรแกรม (How to Run)
เรียกใช้งานส่วนติดต่อผู้ใช้แบบเมนูข้อความ (CLI) ผ่านคำสั่ง:
```bash
python main.py
```
* โปรแกรมจะแสดงเมนูหลักหมายเลข `0` ถึง `10`
* สามารถเลือกหมายเลขเมนูแล้วกด Enter เพื่อสั่งการ (เช่น เพิ่ม/ลดแขก, เพิ่ม/ลดอาคาร, ค้นหาสองทาง, แสดงรายการห้องพัก, รายงานโหลด และส่งออก CSV)
* พิมพ์ `q` ในระหว่างกรอกข้อมูลเมื่อต้องการยกเลิกคำสั่งและกลับสู่เมนูหลัก

---

## 4. วิธีการรันชุดทดสอบอัตโนมัติ (Automated Unit Tests)
สคริปต์ทดสอบครอบคลุมการทำงานหลักและกรณีขอบ (Edge Cases) ทั้งหมด 124 เมธอดทดสอบ สามารถรันคำสั่งจากโฟลเดอร์ Root:
```bash
python -m unittest discover -s tests -t . -v
```
**ผลลัพธ์ที่คาดหวัง:** ต้องขึ้น `Ran 124 tests ... OK` ผ่านทั้งหมด 100%

---

## 5. วิธีการรันการทดลองและสร้างกราฟ (Experiments & Plotting)
1. **รันการทดลองชุด A, B และ C (ทำซ้ำ 3 รอบด้วยค่า salt ต่างกัน):**
   ```bash
   python experiments/run_experiments.py
   ```
   *(ผลลัพธ์จะถูกบันทึกเป็นไฟล์ CSV ลงในโฟลเดอร์ `experiments/results/`)*

2. **ตรวจสอบความถูกต้องของข้อมูลผลการทดลอง:**
   ```bash
   python experiments/verify_results.py
   ```

3. **สร้างกราฟผลการทดลอง (.png) สำหรับเล่มรายงาน:**
   ```bash
   python experiments/plot_charts.py --results experiments/results --out experiments/results
   ```

---

## 6. โครงสร้างโฟลเดอร์ของโปรเจกต์ (Project Structure)
```text
distributed_hilbert_hotel/
├── main.py                   # จุดเริ่มต้นโปรแกรมหลัก (CLI Entry Point)
├── README.md                 # เอกสารแนะนำการติดตั้งและวิธีเรียกใช้งาน
├── requirements.txt          # รายการไลบรารีภายนอกที่ต้องติดตั้ง
├── core/                     # โมดูลตรรกะและอัลกอริทึมหลักของระบบ
│   ├── guest.py              # คลาส Guest และสมการ Cantor Pairing
│   ├── hash_ring.py          # คลาส HashRing, SHA-256 64-bit และ Virtual Nodes
│   ├── hash_mod_n.py         # คลาส HashModN (Baseline)
│   └── hotel_system.py       # คลาส HotelSystem (Controller / Dual Indexing)
├── cli/                      # โมดูลเมนูข้อความติดต่อผู้ใช้งาน (CLI)
│   └── menu.py
├── utils/                    # โมดูลฟังก์ชันช่วยเหลือ
│   ├── metrics.py            # ตัววัดเวลา (time.perf_counter) และ RAM (tracemalloc)
│   └── exporter.py           # ตัวส่งออกไฟล์ CSV (UTF-8)
├── tests/                    # ชุดสคริปต์ทดสอบ Unit Test 124 เมธอด
├── experiments/              # สคริปต์รันการทดลองและพล็อตภาพกราฟ
│   └── results/              # โฟลเดอร์เก็บไฟล์ CSV ข้อมูลผลการทดลอง
└── docs/                     # ไฟล์เล่มรายงาน (Word และ PDF)
```
