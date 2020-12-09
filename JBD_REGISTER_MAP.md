# JBD BMS SERIAL INTERFACE AND REGISTER MAP

## Serial communication 

Serial port communcation is 9600 baud, 8 data bits, no parity, 1 stop bit  (9600 8N1).

### Packet details

Packets to/from the BMS consist of:

<table border="1">
    <tr>
     <th>Start Byte</th>
     <th>Payload</th>
     <th>Checksum</th>
     <th>End Byte</th>
    </tr>
    <tr>
     <td>`0xDD`</td>
     <td>3 or more bytes</td>
     <td>2 bytes, unsigned short</td>
     <td>`0x77`</td>
</table>
<br>

#### Checksum

The checksum is simply sum of the payload byte values subtracted from 0x10000 (65536).

#### Payload to BMS 

<table border="1">
    <tr>
     <td>Command byte: Read: `0x5A`, Write: `0xA5`</th>
     <td>Register Address Byte</th>
     <td>Data length byte</th>
     <td>Data bytes, n = data length byte</th>
    </tr>
</table>

#### Payload from BMS 

<table border="1">
    <tr>
     <td>Register Address Byte</td>
     <td>Command status: OK: `0x0`, Error: `0x80` </td>
     <td>Data length byte</td>
     <td>Data bytes, n = data length byte</td>
    </tr>
</table>

### Register Descriptions

#### Register 0x03 "Basic Info" (READ ONLY)
<table border="1">
    <tr>
     <th>Byte offset</th>
     <th>Data</td>
     <th>Format</th>
     <th>Library field name(s)</th>
    </tr>
    <tr>
     <td>0x0</td>
     <td>Pack voltage</td>
     <td>unsigned 16 bit, unit: 10mV </td>
     <td>pack_mv</td>
    </tr>
    <tr>
     <td>0x2</td>
     <td>Pack amperes</td>
     <td>signed 16 bit, unit: 10mA, negative values are discharge</td>
     <td>pack_ma</td>
    </tr>
    <tr>
     <td>0x4</td>
     <td>Balance Capacity</td>
     <td>unsigned 16 bit, unit: 10mAH</td>
     <td>cycle_cap</td>
    </tr>
    <tr>
     <td>0x6</td>
     <td>Full Capacity</td>
     <td>unsigned 16 bit, unit: 10mAH</td>
     <td>design_cap</td>
    </tr>
    <tr>
     <td>0x8</td>
     <td>Discharge/Charge Cycles</td>
     <td>unsigned 16bit, unit: 1 cycle</td>
     <td>cycle_cnt</td>
    </tr>
    <tr>
     <td>0xA</td>
     <td>Manfuacture date</td>
     <td>16 bits -- bits 15:9=year, 8:5=month, 4:0=Day<br>actual year = year + 2000</td>
     <td>year, month, day</td>
    </tr>
    <tr>
     <td>0xC</td>
     <td>Cell balance status</td>
     <td>16 bits<br>
         bit 0: cell 1 balance active<br>
         bit 1: cell 2 balance active<br>
         ...etc...</td>
     <td>bal_0, bal_1, &lt;etc&gt; </td>
    </tr>
    <tr>
     <td>0xE</td>
     <td>Cell balance status</td>
     <td>16 bits<br>
         bit 0: cell 17 balance active<br>
         bit 1: cell 18 balance active<br>
         ...etc...</td>
     <td>bal_16, bal_17, &lt;etc&gt; </td>
    </tr>
    <tr>
     <td>0x10</td>
     <td>Current errors</td>
     <td>16 bit:<br>
         bit 0: Cell overvolt<br>
         bit 1: Cell undervolt<br>
         bit 2: Pack overvolt<br>
         bit 3: Pack undervolt<br>
         bit 4: Charge overtemp<br>
         bit 5: Charge undertemp<br>
         bit 6: Discharge overtemp<br>
         bit 7: Discharge undertemp<br>
         bit 8: Charge overcurrent<br>
         bit 9: Discharge overcurrent<br>
         bit 10: Short Circuit<br>
         bit 11: Frontend IC error<br>
         bit 12: Charge or Discharge FET locked by config (See register `0x1e` "MOS CTRL")<br>
        </td>
     <td> covp_err, cuvp_err, povp_err, puvp_err, chgot_err, chgut_err, dsgot_err, dsgut_err, chgoc_err, dsgoc_err, sc_err, afe_err, software_err</td>
    </tr>
    <tr>
     <td>0x11</td>
     <td>Software Version</td>
     <td>1 byte, 0x10 = 1.0 (BCD?)</td>
     <td>version</td>
    </tr>
    <tr>
     <td>0x12</td>
     <td>State of Charge</td>
     <td>1 byte, 0-100, percent</td>
     <td>cap_pct</td>
    </tr>
    <tr>
     <td>0x13</td>
     <td>FET status</td>
     <td>1 byte<br>
         bit 0: charge FET <br>
         bit 1: discharge FET<br>
         bit set = FET is conducting</td>
     <td>chg_fet_en, dsg_fet_en</td>
    </tr>
    <tr>
     <td>0x14</td>
     <td>Pack cells</td>
     <td>1 byte, number of series cells in pack</td>
     <td>cell_cnt</td>
    </tr>
    <tr>
     <td>0x15</td>
     <td>NTC count</td>
     <td>1 byte, number of thermistors</td>
     <td>ntc_cnt</td>
    </tr>
    <tr>
     <td>0x16 .. 0x16 + ntc_cnt x 2</td>
     <td>NTC Values</td>
     <td>16 bits, unsigned, Kelvin / 10</td>
     <td>ntc0, ntc1, &lt;etc&gt;</td>
    </tr>
</table>


#### Register 0x04 "Cell voltages" (READ ONLY)
The number of values returned depends on the `cell_cnt` field from 0x3 "Basic Info".
<table border="1">
    <tr>
     <th>Byte offset</th>
     <th>Data</td>
     <th>Format</th>
     <th>Field name(s)</t.>
    </tr>
    <tr>
     <td>2 * cell number (starting at zero)</td>
     <td>Cell voltage</td>
     <td>16 bits, unsigned, unit: 1mV</td>
     <td>cell0_mv, cell1_mv, &lt;etc&gt;</td>
    </tr>
</table>

#### Register 0x05 "Device Name" (READ ONLY)
The number of values returned depends on the `cell_cnt` field from 0x3 "Basic Info".
<table border="1">
    <tr>
     <th>Byte offset</th>
     <th>Data</td>
     <th>Format</th>
     <th>Field name(s)</t.>
    </tr>
    <tr>
     <td>0x0</td>
     <td>Device name length</td>
     <td>1 byte, length of following string</td>
     <td>&lt;N/A&gt;</td>
    </tr>
    <tr>
     <td>0x1 .. n</td>
     <td>Device name </td>
     <td>n bytes of device name</td>
     <td>device_name</td>
    </tr>
</table>

### EEPROM Register Descriptions
These registers are read/write configuration settings that are stored in EEPROM.  They affect the operation of the BMS.

#### Register 0x00 "Enter factory Mode"
Write the byte sequence 0x56, 0x78 to enter "Factory Mode."  In this mode, the other registers below can be accessed.

#### Register 0x01 "Exit factory Mode"
Write the byte sequence 0x0, 0x0 to exit "Factory Mode," and update the values in the EEPROM.

Write the byte sequence 0x28, 0x28 to exit "Factory Mode," update the values in the EEROM, and reset the "Error Counts" register to zeroes.


#### Register 0x05 "Device Name" (READ ONLY)
The number of values returned depends on the `cell_cnt` field from 0x3 "Basic Info".
<table border="1">
    <tr>
     <th>Byte offset</th>
     <th>Data</td>
     <th>Format</th>
     <th>Field name(s)</t.>
    </tr>
    <tr>
     <td>0x0</td>
     <td>Device name length</td>
     <td>1 byte, length of following string</td>
     <td>&lt;N/A&gt;</td>
    </tr>
    <tr>
     <td>0x1 .. n</td>
     <td>Device name </td>
     <td>n bytes of device name</td>
     <td>device_name</td>
    </tr>
</table>