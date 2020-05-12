from base64 import b64decode
from bitn import BitBin
import json
from threefive import (
    descriptors as dscprs,
    splice_info_section as spinfo,
    splice_commands as spcmd)


class Splice:
    '''
    The threefive.Splice class handles parsing
    SCTE 35 message strings.
    '''
    # map of known descriptors and associated classes
    descriptor_map = {0: dscprs.Avail_Descriptor,
                      1: dscprs.Dtmf_Descriptor,
                      2: dscprs.Segmentation_Descriptor,
                      3: dscprs.Time_Descriptor,
                      4: dscprs.Audio_Descriptor}
    
    # map of known splice commands and associated classes
    command_map = {0: spcmd.Splice_Null,
                   4: spcmd.Splice_Schedule,
                   5: spcmd.Splice_Insert,
                   6: spcmd.Time_Signal,
                   7: spcmd.Bandwidth_Reservation,
                   255: spcmd.Private_Command}

    def __init__(self, mesg,pid = False,pts = False):
        self.mesg = self.mkbits(mesg)
        self.pid = pid
        self.pts = pts
        self.infobb = BitBin(self.mesg[:14])
        self.mesg = self.mesg[14:]
        self.info_section = spinfo.Splice_Info_Section()
        self.info_section.decode(self.infobb)
        self.descriptors = []
        cmdl = self.info_section.splice_command_length
        # fix for bad self.info_section.splice_command_length 
        if cmdl > 174:   # 188 bytes per packet - 14 bytes for splice_info_section
            self.cmdbb = BitBin(self.mesg)
            self.set_splice_command()
            self.mesg = self.mesg[self.command.splice_command_length:]
            self.info_section.splice_command_length = self.command.splice_command_length
        else:
            self.cmdbb = BitBin(self.mesg[:cmdl])
            self.set_splice_command()
            self.mesg = self.mesg[cmdl:]
        self.descriptorloop()
        self.info_section.crc = hex(int.from_bytes(self.mesg[0:4],byteorder = 'big'))

    def __repr__(self):
        return str(self.get())

    def descriptorloop(self):
        '''
        parses all splice descriptors
        '''
        dll = self.info_section.descriptor_loop_length = int.from_bytes(self.mesg[0:2],byteorder = 'big')
        self.mesg = self.mesg[2:]
        while dll > 0:
            try:
                sd = self.set_splice_descriptor()
                sdl = sd.descriptor_length
                dll-= sdl+2
                self.descriptors.append(sd)
            except:
                break
  
    def get(self):
        '''
        Returns a dict of dicts for all three parts
        of a SCTE 35 message.
        '''
        scte35 = {**self.get_info_section(),
                    **self.get_command(),
                    **self.get_descriptors()}
        if self.pid or self.pts:
            scte35.update(self.get_packet_data())
        return scte35    

    def get_command(self):
        '''
        returns the SCTE 35
        splice command data as a dict.
        '''  
        return {'Splice_Command': vars(self.command)}
    
    def get_descriptors(self):
        '''
        Returns a list of SCTE 35
        splice descriptors as dicts.
        '''
        return {'Splice_Descriptors': self.list_descriptors()}
     
    def get_info_section(self):
        '''
        Returns SCTE 35
        splice info section as a dict
        '''
        return {'Info_Section':vars(self.info_section)}

    def get_packet_data(self):
        packet = {}
        if self.pid: packet['pid'] = hex(self.pid)
        if self.pts: packet['pts'] = self.pts
        return {'Packet_Data':packet}

    def kvprint(self, obj):
        print('\n')
        print(json.dumps({'SCTE35':obj},indent = 8))

    def list_descriptors(self):
        '''
        returns SCTE 35 splice descriptors in list
        '''
        return [vars(d) for d in self.descriptors]

    def mkbits(self, s):
        '''
        Convert Hex and Base64 strings into bytes.
        '''
        if s[:2].lower() == '0x': s = s[2:]
        if s[:2].lower() == 'fc': return bytes.fromhex(s)
        try: return b64decode(s)
        except: return s

    def set_splice_command(self):
        '''
        Splice Commands looked up in self.command_map
        '''
        sct = self.info_section.splice_command_type
        if sct not in self.command_map.keys():
            raise ValueError('Unknown Splice Command Type')
            return False
        self.command = self.command_map[sct]()
        self.command.decode(self.cmdbb)

    def set_splice_descriptor(self):
        '''
        Splice Descriptors looked up in self.descriptor_map
        '''
        # splice_descriptor_tag 8 uimsbf
        tag = self.mesg[0]
        desc_len = self.mesg[1]
        self.mesg = self.mesg[2:]
        bitbin = BitBin(self.mesg[:desc_len])
        self.mesg = self.mesg[desc_len:]
        if tag in self.descriptor_map.keys():
            sd = self.descriptor_map[tag](bitbin,tag)
            sd.descriptor_length = desc_len
            return sd
        else: return False

    def show(self):
        '''
        pretty prints the SCTE 35 message
        '''    
        self.kvprint(self.get())

    def show_command(self):
        '''
        pretty prints SCTE 35 splice command
        '''
        self.kvprint(self.get_command())
        
    def show_descriptors(self):
        '''
        pretty prints SCTE 35 splice descriptors
        '''
        self.kvprint(self.get_descriptors())

    def show_info_section(self):
        '''
        pretty prints SCTE 35 splice info section
        '''
        self.kvprint(self.get_info_section())
