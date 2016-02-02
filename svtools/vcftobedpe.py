import argparse
import sys
import time
import re

class Reader(object):
    def __init__(self):
        self.file_format = 'BEDPE'
        self.reference = ''
        self.sample_list = []
        self.info_list = []
        self.format_list = []
        self.alt_list = []
        self.add_format('GT', 1, 'String', 'Genotype')
        self.misc = list()

    def add_header(self, header):
        for line in header:
            if line.split('=')[0] == '##fileformat':
                self.file_format = line.rstrip().split('=')[1]
            elif line.split('=')[0] == '##reference':
                self.reference = line.rstrip().split('=')[1]
            elif line.split('=')[0] == '##INFO':
                a = line[line.find('<')+1:line.find('>')]
                r = re.compile(r'(?:[^,\"]|\"[^\"]*\")+')
                self.add_info(*[b.split('=')[1] for b in r.findall(a)])
                if  self.info_list[len(self.info_list)-1].id == "SVTYPE":
                    self.add_info("POS",1,'Integer','Position of the variant described in this record')
            elif line.split('=')[0] == '##ALT':
                a = line[line.find('<')+1:line.find('>')]
                r = re.compile(r'(?:[^,\"]|\"[^\"]*\")+')
                self.add_alt(*[b.split('=')[1] for b in r.findall(a)])
            elif line.split('=')[0] == '##FORMAT':
                a = line[line.find('<')+1:line.find('>')]
                r = re.compile(r'(?:[^,\"]|\"[^\"]*\")+')
                self.add_format(*[b.split('=')[1] for b in r.findall(a)])
            elif line.startswith('##') and not line.startswith('##fileDate'):
                self.misc.append(line.rstrip())
            elif line[0] == '#' and line[1] != '#':
                self.sample_list = line.rstrip().split('\t')[9:]
                
    # return the VCF header
    def get_header(self):
        header = '\n'.join(['##fileformat=' + self.file_format,
                            '##fileDate=' + time.strftime('%Y%m%d'),
                            '##reference=' + self.reference] + \
                           [i.hstring for i in self.info_list] + \
                           [a.hstring for a in self.alt_list] + \
                           [f.hstring for f in self.format_list] + \
                           [l for l in self.misc] + \
                           ['\t'.join([
                               '#CHROM',
                               'POS',
                               'ID',
                               'REF',
                               'ALT',
                               'QUAL',
                               'FILTER',
                               'INFO',
                               'FORMAT'] + \
                                      self.sample_list
                                  )])
        return header

    def add_info(self, id, number, type, desc):
        if id not in [i.id for i in self.info_list]:
            inf = Info(id, number, type, desc)
            self.info_list.append(inf)
            
    def add_alt(self, id, desc):
        if id not in [a.id for a in self.alt_list]:
            alt = Alt(id, desc)
            self.alt_list.append(alt)

    def add_format(self, id, number, type, desc):
        if id not in [f.id for f in self.format_list]:
            fmt = Format(id, number, type, desc)
            self.format_list.append(fmt)

    def add_sample(self, name):
        self.sample_list.append(name)

class Info(object):
    def __init__(self, id, number, type, desc):
        self.id = str(id)
        self.number = str(number)
        self.type = str(type)
        self.desc = str(desc)
        # strip the double quotes around the string if present
        if self.desc.startswith('"') and self.desc.endswith('"'):
            self.desc = self.desc[1:-1]
        self.hstring = '##INFO=<ID=' + self.id + ',Number=' + self.number + ',Type=' + self.type + ',Description=\"' + self.desc + '\">'

class Alt(object):
    def __init__(self, id, desc):
        self.id = str(id)
        self.desc = str(desc)
        # strip the double quotes around the string if present
        if self.desc.startswith('"') and self.desc.endswith('"'):
            self.desc = self.desc[1:-1]
        self.hstring = '##ALT=<ID=' + self.id + ',Description=\"' + self.desc + '\">'

class Format(object):
    def __init__(self, id, number, type, desc):
        self.id = str(id)
        self.number = str(number)
        self.type = str(type)
        self.desc = str(desc)
        # strip the double quotes around the string if present
        if self.desc.startswith('"') and self.desc.endswith('"'):
            self.desc = self.desc[1:-1]
        self.hstring = '##FORMAT=<ID=' + self.id + ',Number=' + self.number + ',Type=' + self.type + ',Description=\"' + self.desc + '\">'

class Variant(object):
    def __init__(self, var_list, vcf):
        self.chrom = var_list[0]
        self.pos = int(var_list[1])
        self.var_id = var_list[2]
        self.ref = var_list[3]
        self.alt = var_list[4]
        self.qual = var_list[5]
        self.filter = var_list[6]
        self.sample_list = vcf.sample_list
        self.info_list = vcf.info_list
        self.info = dict()
        self.format_list = vcf.format_list
        self.active_formats = set()
        self.gts = dict()
        # make a genotype for each sample at variant
        for i in xrange(len(self.sample_list)):
            s_gt = var_list[9+i].split(':')[0]
            s = self.sample_list[i]
            self.gts[s] = Genotype(self, s, s_gt)
        # import the existing fmt fields
        for i in xrange(len(self.sample_list)):
            s = self.sample_list[i]
            for j in zip(var_list[8].split(':'), var_list[9+i].split(':')):
                self.gts[s].set_format(j[0], j[1])

        self.info = dict()
        i_split = [a.split('=') for a in var_list[7].split(';')] # temp list of split info column
        for i in i_split:
            if len(i) == 1:
                i.append(True)
            self.info[i[0]] = i[1]
        #Adding info field pos in header
        self.info["POS"] = self.pos
            
        
       
    def set_info(self, field, value):
        if field in [i.id for i in self.info_list]:
            self.info[field] = value
        else:
            sys.stderr.write('\nError: invalid INFO field, \"' + field + '\"\n')
            exit(1)

    def get_info(self, field):
        return self.info[field]

    def get_info_string(self):
        i_list = list()
        for info_field in self.info_list:
            if info_field.id in self.info.keys():
                if info_field.type == 'Flag':
                    i_list.append(info_field.id)
                else:
                    i_list.append('%s=%s' % (info_field.id, self.info[info_field.id]))
        return ';'.join(i_list)

    def get_format_string(self):
        f_list = list()
        for f in self.format_list:
            if f.id in self.active_formats:
                f_list.append(f.id)
        return ':'.join(f_list)

    def genotype(self, sample_name):
        if sample_name in self.sample_list:
            return self.gts[sample_name]
        else:
            sys.stderr.write('\nError: invalid sample name, \"' + sample_name + '\"\n')

    def get_var_string(self):
        s = '\t'.join(map(str,[
            self.chrom,
            self.pos,
            self.var_id,
            self.ref,
            self.alt,
            '%0.2f' % self.qual,
            self.filter,
            self.get_info_string(),
            self.get_format_string(),
            '\t'.join(self.genotype(s).get_gt_string() for s in self.sample_list)
        ]))
        return s

class Genotype(object):
    def __init__(self, variant, sample_name, gt):
        self.format = dict()
        self.variant = variant
        self.set_format('GT', gt)

    def set_format(self, field, value):
        if field in [i.id for i in self.variant.format_list]:
            self.format[field] = value
            if field not in self.variant.active_formats:
                self.variant.active_formats.add(field)
        # else:
        #     sys.stderr.write('\nError: invalid FORMAT field, \"' + field + '\"\n')
        #     exit(1)

    def get_format(self, field):
        return self.format[field]

    def get_gt_string(self):
        g_list = list()
        for f in self.variant.format_list:
            if f.id in self.variant.active_formats:
                if f.id in self.format:
                    if type(self.format[f.id]) == float:
                        g_list.append('%0.2f' % self.format[f.id])
                    else:
                        g_list.append(self.format[f.id])
                else:
                    g_list.append('.')
        return ':'.join(map(str,g_list))

def writeBND(prim, sec, v, bedpe_out):
    '''
    Parse out strand orientation from BND alt fields
    Simple mapping seems to be left-most strand corresponds to the direction of the square brackets. Right-most to side the reference base is on.

    For example:

    N[2:22222[ -> brackets pt left so - and N is on the left so plus +-
    ]2:22222]N -> brackets pt right so + and N is on the right so minus -+
    N]2:222222] -> brackets pt right so + and N is on the left so plus ++
    [2:222222[N -> brackets pt left so + and N is on the right so minus --
    '''
    primary = prim
    secondary = sec
    if prim is None:
        primary = sec 
    b1 = primary.pos
    o1 = '+'
    o2 = '+'
    sep = ']'
    if ']' not in primary.alt:
        sep = '['
        o2 = '-'
    if primary.alt.startswith('[') or primary.alt.startswith(']'):
            o1 = '-'
    r = re.compile(r'\%s(.+?)\%s' % (sep, sep))
    chrom2, b2 = r.findall(primary.alt)[0].split(':')
    b2 = int(b2)
    primary.set_info('END',b2)
    score = v[5]
    # XXX Colby mentioned that coordinates are 0 based sometimes
    # and not 0-based other times. This appears to be code pertaining to that
    # If reference is on the right of the brackets, o1 == '-' and coords adjusted
    if 'CIPOS' in primary.info:
        span = map(int, primary.info['CIPOS'].split(','))
        if o1 == '-':
            span[0]-=1
            span[1]-=1
        s1 = b1 + span[0]
        e1 = b1 + span[1]
    else:
        if o1 == '-':
            e1 = b1 - 1
            s1 = b1 - 1
        else:
            e1 = b1
            s1 = b1
    
    if 'CIEND' in primary.info:    
        span = map(int, primary.info['CIEND'].split(','))
        if o2 == '-':
            span[0]-=1
            span[1]-=1
        s2 = b2 + span[0]
        e2 = b2 + span[1]
    else:
        if o2== '-':
            e2 = b2 - 1
            s2 = b2 - 1
        else:
            e2 = b2
            s2 = b2

    ispan = s2 - e1
    ospan = e2 - s1
    chrom_A = primary.chrom
    chrom_B = chrom2
    
    # write bedpe
    #Swap fields for no primary present as we did calculation with secondary
    if prim is None:
        info_A = "MISSING"
        chrom_A = chrom2
        chrom_B = primary.chrom
        s1, s2 = s2, s1
        e1, e2 = e2, e1
        o1, o2 = o2, o1
    else:
        info_A = primary.get_info_string()    
    if sec is None:
        info_B = "MISSING"
    else:
        info_B = secondary.get_info_string()    
    bedpe_out.write('\t'.join(map(str,
                                  [chrom_A,
                                   max(s1,0),
                                   max(e1,0),
                                   chrom_B,
                                   max(s2,0),
                                   max(e2,0),
                                   primary.info['EVENT'],
                                   primary.qual,
                                   o1,
                                   o2,
                                   primary.info['SVTYPE'],
                                   primary.filter] + [info_A] + [info_B] + v[8:]
                                  )) + '\n')
# primary function
def vcfToBedpe(vcf_file, bedpe_out):
    vcf = Reader()
    in_header = True
    header = []
    sample_list = []
    bnds = dict()
    sec_bnds = dict()
    v = []
    for line in vcf_file:
        if in_header:
            if line[0:2] == '##':
                if line.split('=')[0] == '##fileformat':
                    line = '##fileformat=' + "BEDPE" + '\n'
                if line.split('=')[0] == '##fileDate':
                    line = '##fileDate=' + time.strftime('%Y%m%d') + '\n'
                header.append(line)
                continue
            elif line[0] == '#' and line[1] != '#':    
                sample_list = line.rstrip().split('\t')[9:]
                continue
            else:
                # print header
                in_header = False
                vcf.add_header(header)
                header=vcf.get_header()
                bedpe_out.write(header[:header.rfind('\n')] + '\n')                
                if len(sample_list) > 0:
                    bedpe_out.write('\t'.join(['#CHROM_A',
                                               'START_A',
                                               'END_A',
                                               'CHROM_B',
                                               'START_B',
                                               'END_B',
                                               'ID',
                                               'QUAL',
                                               'STRAND_A',
                                               'STRAND_B',
                                               'TYPE',
                                               'FILTER',
                                               'INFO_A','INFO_B',
                                               'FORMAT','\t'.join(map(str,sample_list))] 
                                             ) + '\n')
                else:
                    bedpe_out.write('\t'.join(['#CHROM_A',
                                               'START_A',
                                               'END_A',
                                               'CHROM_B',
                                               'START_B',
                                               'END_B',
                                               'ID',
                                               'QUAL',
                                               'STRAND_A',
                                               'STRAND_B',
                                               'TYPE',
                                               'FILTER',
                                               'INFO_A','INFO_B']
                                              ) + '\n')

        v = line.rstrip().split('\t')
        var = Variant(v, vcf)
        if var.info['SVTYPE'] != 'BND':
            b1 = var.pos
            b2 = int(var.info['END'])
            name = v[2]
            score = v[5]
            if 'STRANDS' in var.info:
                strands = var.info['STRANDS']
                o1 = strands[0]
                o2 = strands[1]
            else:
                o1 = '+'
                o2 = '+'
            if 'CIPOS' in var.info:
                span = map(int, var.info['CIPOS'].split(','))
                s1 = b1 + span[0]
                e1 = b1 + span[1]
            else:
                e1 = b1
                s1 = b1
            if 'CIEND' in var.info:    
                span = map(int, var.info['CIEND'].split(','))
                s2 = b2 + span[0]
                e2 = b2 + span[1]
            else:
                e2 = b2
                s2 = b2    

            ispan = s2 - e1
            ospan = e2 - s1
            # write bedpe
            bedpe_out.write('\t'.join(map(str,
                                          [var.chrom,
                                           max(s1,0),
                                           max(e1,0),
                                           var.chrom,
                                           max(s2,0),
                                           max(e2,0),
                                           name,
                                           var.qual,
                                           o1,
                                           o2,
                                           var.info['SVTYPE'],
                                           var.filter] +
                                           [var.get_info_string()] + ['.'] + v[8:]
                                          )) + '\n')
        else:
            if 'SECONDARY' in var.info:
                if var.info['EVENT'] in bnds:
                    #primary
                    var1 = bnds[var.info['EVENT']]
                    writeBND(var1,var,v,bedpe_out)
                    del bnds[var.info['EVENT']]                              
                else:
                    sec_bnds.update({var.info['EVENT']:var})
            else: 
                bnds.update({var.info['EVENT']:var})
                continue
    intersected_keys = bnds.viewkeys() & sec_bnds.viewkeys()
    for key in intersected_keys:
       writeBND(bnds[key],sec_bnds[key],v,bedpe_out)
       del bnds[key] 
       del sec_bnds[key]
    if bnds is not None:
        for bnd in bnds:
            sys.stderr.write('Warning: missing secondary multiline variant at ID:' + bnds[bnd].info['EVENT'] + '\n')
            writeBND(bnds[bnd],None,v,bedpe_out)
    if sec_bnds is not None:
        for bnd in sec_bnds:
            sys.stderr.write('Warning: missing primary multiline variant at ID:' + sec_bnds[bnd].info['EVENT'] + '\n')
            writeBND(None,sec_bnds[bnd],v,bedpe_out)
            
    # close the files
    bedpe_out.close()
    vcf_file.close()

    return

def description():
    return 'Convert a VCF file to a BEDPE file'

def add_arguments_to_parser(parser):
    parser.add_argument('-i', '--input', type=argparse.FileType('r'), default=None, help='VCF input (default: stdin)')
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout, help='Output BEDPE to write (default: stdout)')
    parser.set_defaults(entry_point=run_from_args)

def command_parser():
    parser = argparse.ArgumentParser(description=description())
    add_arguments_to_parser(parser)
    return parser

def run_from_args(args):
    if args.input == None:
        if sys.stdin.isatty():
            parser.print_help()
            sys.exit(1)
        else:
            args.input = sys.stdin
    return vcfToBedpe(args.input, args.output)

# initialize the script
if __name__ == '__main__':
    parser = command_parser()
    args = parser.parse_args()
    sys.exit(args.entry_point(args))
