#!/usr/bin/env python3
"""Build editable DOCX, IEEEtran source and an IEEE-style reading PDF from one manuscript.

The PDF uses Matplotlib's embedded-font backend because TeX/Word conversion is
unavailable in this environment. IEEEtran source is provided for venue compilation.
"""
from pathlib import Path
import os,re,json,struct
from xml.sax.saxutils import escape
from zipfile import ZipFile,ZIP_DEFLATED
from functools import lru_cache

ROOT=Path(__file__).resolve().parents[1];PAPER=ROOT/'paper'
os.environ.setdefault('MPLCONFIGDIR','/tmp/research-paper-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextToPath

TITLE='Literature-Grounded Research Idea Generation Using Specialized Multi-Agent Reviewers: A Pilot Study'
AUTHORS='Safee Ahmad, Ahmed Izaan, and Fatima Ajmal'
AFFILIATION='National University of Computer and Emerging Sciences (FAST–NUCES), Islamabad, Pakistan'


def parse():
    lines=(PAPER/'manuscript.md').read_text().splitlines();blocks=[];i=0;active=False;section=''
    while i<len(lines):
        line=lines[i].strip()
        if line.startswith('## '):
            active=True;section=line[3:];blocks.append(('heading',section));i+=1;continue
        if not active or not line:i+=1;continue
        if line.startswith('### '):blocks.append(('subheading',line[4:]));i+=1;continue
        if line.startswith('!['):
            m=re.fullmatch(r'!\[(.*)\]\((.*)\)',line);blocks.append(('figure',m.group(1),m.group(2)));i+=1;continue
        if line.startswith('TABLE '):blocks.append(('table_caption',line));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c) for c in row):rows.append(row)
                i+=1
            blocks.append(('table',rows));continue
        para=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith('#'):
            para.append(lines[i].strip());i+=1
        blocks.append(('reference' if section=='References' else 'abstract' if section=='Abstract' else 'keywords' if section=='Index Terms' else 'paragraph',' '.join(para)))
    return blocks


def tex_escape(text):
    text=text.replace('−','-').replace('–','--').replace('—','---').replace('→',r'$\rightarrow$').replace('≤',r'$\leq$')
    text=text.replace('“','``').replace('”',"''").replace('’',"'")
    return ''.join({'&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}'}.get(c,c) for c in text)

def cite_tex(text):
    # Escape text first; source citations are plain numeric brackets.
    return re.sub(r'\[(\d+)\]',lambda m:r'\cite{r'+m[1]+'}',tex_escape(text))

def build_tex(blocks):
    out=[r'\documentclass[conference]{IEEEtran}',r'\usepackage[T1]{fontenc}',r'\usepackage[utf8]{inputenc}',
         r'\usepackage{graphicx,booktabs,cite,url,balance}',r'\title{'+tex_escape(TITLE)+'}',
         r'\author{\IEEEauthorblockN{'+tex_escape(AUTHORS)+'}'+r'\IEEEauthorblockA{'+tex_escape(AFFILIATION)+'}}',r'\begin{document}',r'\maketitle']
    skip={'Abstract','Index Terms','References'};table_caption=None
    for kind,*data in blocks:
        if kind=='heading':
            title=data[0]
            if title in skip:continue
            if title=='Acknowledgment':out.append(r'\section*{Acknowledgment}')
            else:out.append(r'\section{'+tex_escape(re.sub(r'^[IVX]+\.\s*','',title))+'}')
        elif kind=='subheading':out.append(r'\subsection{'+tex_escape(re.sub(r'^[A-Z]\.\s*','',data[0]))+'}')
        elif kind=='abstract':out.append(r'\begin{abstract}'+tex_escape(data[0])+r'\end{abstract}')
        elif kind=='keywords':out.append(r'\begin{IEEEkeywords}'+tex_escape(data[0])+r'\end{IEEEkeywords}')
        elif kind=='paragraph':out.append(cite_tex(data[0])+'\n')
        elif kind=='table_caption':table_caption=re.sub(r'^TABLE [IVX]+\.\s*','',data[0])
        elif kind=='table':
            rows=data[0];n=len(rows[0]);out.extend([r'\begin{table}[t]',r'\centering',r'\caption{'+tex_escape(table_caption or '')+'}',r'\scriptsize',r'\setlength{\tabcolsep}{3pt}',r'\begin{tabular}{l'+('r'*(n-1))+'}',r'\toprule'])
            for index,row in enumerate(rows):
                out.append(' & '.join(tex_escape(c) for c in row)+r' \\')
                if index==0:out.append(r'\midrule')
            out.extend([r'\bottomrule',r'\end{tabular}',r'\end{table}']);table_caption=None
        elif kind=='figure':
            caption,path=data;out.extend([r'\begin{figure}[t]',r'\centering',r'\includegraphics[width=\columnwidth]{'+str(Path(path).with_suffix('.pdf'))+'}',r'\caption{'+tex_escape(re.sub(r'^Figure \d+\.\s*','',caption))+'}',r'\end{figure}'])
    refs=[b[1] for b in blocks if b[0]=='reference'];out.append(r'\balance');out.append(r'\begin{thebibliography}{99}')
    for ref in refs:
        m=re.match(r'\[(\d+)\]\s*(.*)',ref);out.append(r'\bibitem{r'+m[1]+'} '+tex_escape(m[2]))
    out.extend([r'\end{thebibliography}',r'\end{document}'])
    (PAPER/'main.tex').write_text('\n'.join(out)+'\n')

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def run(text,bold=False,italic=False,size=None):
    pr=('<w:b/>' if bold else '')+('<w:i/>' if italic else '')+(f'<w:sz w:val="{size}"/>' if size else '')
    return '<w:r>'+('<w:rPr>'+pr+'</w:rPr>' if pr else '')+'<w:t xml:space="preserve">'+escape(text)+'</w:t></w:r>'

def para(text,style='Normal',align=None,bold=False,italic=False,size=None,keep=False):
    pr=f'<w:pStyle w:val="{style}"/>'+(f'<w:jc w:val="{align}"/>' if align else '')+('<w:keepNext/>' if keep else '')
    return '<w:p><w:pPr>'+pr+'</w:pPr>'+run(text,bold,italic,size)+'</w:p>'

def section(cols):
    return f'<w:sectPr><w:type w:val="continuous"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:bottom="1440" w:left="900" w:right="900" w:header="0" w:footer="0"/><w:cols w:num="{cols}" w:space="360"/></w:sectPr>'

def build_docx(blocks):
    body=[para(TITLE,'Title'),para(AUTHORS,'Authors'),para(AFFILIATION,'Affiliation'),'<w:p><w:pPr>'+section(1)+'</w:pPr></w:p>']
    images=[];relationships=[]
    for kind,*data in blocks:
        if kind=='heading':
            if data[0] not in {'Abstract','Index Terms','References'}:body.append(para(data[0].upper(),'Heading1',keep=True))
            elif data[0]=='References':body.append(para('REFERENCES','Heading1',keep=True))
        elif kind=='subheading':body.append(para(data[0],'Heading2',keep=True))
        elif kind=='abstract':body.append(para('Abstract—'+data[0],'Abstract',bold=True))
        elif kind=='keywords':body.append(para('Index Terms—'+data[0],'Abstract',italic=True))
        elif kind=='paragraph':body.append(para(data[0]))
        elif kind=='reference':body.append(para(data[0],'Reference'))
        elif kind=='table_caption':body.append(para(data[0],'Caption',align='center',keep=True))
        elif kind=='table':
            rows=data[0];count=len(rows[0]);widths=([1840]+[640]*5 if count==6 else [2160]+[1440]*(count-1) if count==3 else [1680]*count)
            table=['<w:tbl><w:tblPr><w:tblW w:w="5040" w:type="dxa"/><w:tblLayout w:type="fixed"/><w:tblBorders><w:top w:val="single" w:sz="4"/><w:bottom w:val="single" w:sz="4"/></w:tblBorders></w:tblPr><w:tblGrid>']
            table.extend(f'<w:gridCol w:w="{width}"/>' for width in widths);table.append('</w:tblGrid>')
            for index,row in enumerate(rows):
                table.append('<w:tr><w:trPr><w:cantSplit/>'+('<w:tblHeader/>' if index==0 else '')+'</w:trPr>')
                for col,text in enumerate(row):
                    table.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[col]}" w:type="dxa"/>'+('<w:tcBorders><w:bottom w:val="single" w:sz="4"/></w:tcBorders>' if index==0 else '')+'</w:tcPr>'+para(text,'TableText',align='left' if col==0 else 'center',bold=index==0)+'</w:tc>')
                table.append('</w:tr>')
            table.append('</w:tbl>');body.append(''.join(table))
        elif kind=='figure':
            caption,source=data;image=PAPER/source;blob=image.read_bytes();pxw,pxh=struct.unpack('>II',blob[16:24]);cx=3200400;cy=int(cx*pxh/pxw);i=len(images)+1
            images.append((f'fig{i}.png',blob));relationships.append(f'<Relationship Id="img{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/fig{i}.png"/>')
            draw=f'''<w:p><w:pPr><w:keepNext/><w:jc w:val="center"/></w:pPr><w:r><w:drawing><wp:inline><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{i}" name="Figure {i}" descr="{escape(caption)}"/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="fig{i}.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="img{i}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'''
            body.extend([draw,para(caption,'Caption')])
    body.append(section(2))
    namespaces=f'xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"'
    document=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {namespaces}><w:body>'+''.join(body)+'</w:body></w:document>'
    styles=f'''<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman"/><w:sz w:val="20"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="both"/><w:ind w:firstLine="180"/></w:pPr></w:pPrDefault></w:docDefaults>'''
    for name,size,align,extra in [('Normal',20,'both',''),('Title',44,'center',''),('Authors',22,'center',''),('Affiliation',18,'center',''),('Heading1',20,'center','<w:smallCaps/>'),('Heading2',20,'left','<w:i/>'),('Abstract',18,'both',''),('Reference',16,'left',''),('Caption',16,'left',''),('TableText',16,'left','')]:
        before=120 if name in ['Heading1','Heading2'] else 0;after=80 if name in ['Title','Authors','Affiliation','Heading1','Heading2','Caption'] else 0
        styles+=f'<w:style w:type="paragraph" w:styleId="{name}"><w:name w:val="{name}"/><w:pPr><w:jc w:val="{align}"/><w:spacing w:before="{before}" w:after="{after}"/><w:ind w:firstLine="{180 if name=="Normal" else 0}"/></w:pPr><w:rPr><w:sz w:val="{size}"/>{extra}</w:rPr></w:style>'
    styles+='</w:styles>'
    content='''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>'''
    with ZipFile(PAPER/'Research_Paper_IEEE.docx','w',ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml',content)
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="main" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr('word/document.xml',document);z.writestr('word/styles.xml',styles)
        z.writestr('word/_rels/document.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'+''.join(relationships)+'</Relationships>')
        for name,blob in images:z.writestr('word/media/'+name,blob)

FONT_DIR=Path('/usr/share/fonts/truetype/liberation')
@lru_cache(maxsize=16)
def font(size=10,style='normal'):
    suffix={'normal':'Regular','bold':'Bold','italic':'Italic'}[style]
    return FontProperties(fname=str(FONT_DIR/f'LiberationSerif-{suffix}.ttf'),size=size)
TEXTPATH=TextToPath()
@lru_cache(maxsize=20000)
def width(text,size=10,style='normal'):
    return TEXTPATH.get_text_width_height_descent(text,font(size,style),False)[0]

def wrap(text,available,size=10,style='normal',first_indent=0):
    words=text.split();lines=[];line=[];length=0;target=available-first_indent
    for word in words:
        delta=width(word,size,style)+(width(' ',size,style) if line else 0)
        if line and length+delta>target:
            lines.append(' '.join(line));line=[word];length=width(word,size,style);target=available
        else:line.append(word);length+=delta
    if line:lines.append(' '.join(line))
    return lines

class ReadingPDF:
    def __init__(self,path):
        self.pdf=PdfPages(path);self.pdf.infodict().update(Title=TITLE,Author=AUTHORS,Subject='IEEE-style conference pilot paper; see main.tex for IEEEtran source')
        self.col=0;self.page_no=0;self.fig=None;self.pending=[];self.layouts=[];self.new_page()
    def new_page(self):
        if self.fig is not None:self.pdf.savefig(self.fig);plt.close(self.fig)
        self.line_calls=[];self.page_no+=1;self.fig=plt.figure(figsize=(8.5,11),facecolor='white');self.col=0;self.top=54;self.y=54
        if self.page_no==1:
            for line in wrap(TITLE,522,22):self.line(line,45,self.y,522,22,align='center');self.y+=25
            self.y+=7;self.line(AUTHORS,45,self.y,522,11,align='center');self.y+=16
            for line in wrap(AFFILIATION,522,9):self.line(line,45,self.y,522,9,align='center');self.y+=11
            self.top=self.y+20;self.y=self.top
    @property
    def x(self):return 45+self.col*270
    def line(self,text,x,y,w=252,size=10,style='normal',justify=False,align='left'):
        # All coordinates are points from the top-left of US Letter paper.
        self.line_calls.append({'text':text,'y':y})
        def draw_text(px,content):
            artist=self.fig.text(px/612,1-(y+size)/792,content,fontproperties=font(size,style),va='baseline')
            artist._paper_y=y
            return artist
        if align=='center':x+=(w-width(text,size,style))/2
        words=text.split(' ')
        if justify and len(words)>1:
            widths=[width(v,size,style) for v in words];space=(w-sum(widths))/(len(words)-1)
            if 0<=space<=2.5*width(' ',size,style):
                for word,span in zip(words,widths):draw_text(x,word);x+=span+space
                return
        draw_text(x,text)
    def next_column(self):
        if self.col==0:self.col=1;self.y=self.top
        else:self.new_page()
        while self.pending and self.y+self.pending[0][0]<=720:
            _,draw=self.pending.pop(0);draw()
    def ensure(self,height):
        while self.y+height>720:self.next_column()
    def paragraph(self,text,size=10,style='normal',indent=True,space=4):
        lines=wrap(text,252,size,style,10 if indent else 0);leading=size*1.12
        self.ensure(min(2,len(lines))*leading)
        for i,line in enumerate(lines):
            self.ensure(leading);pad=10 if indent and i==0 else 0
            self.line(line,self.x+pad,self.y,252-pad,size,style,justify=i<len(lines)-1)
            self.y+=leading
        self.y+=space
    def heading(self,text,sub=False):
        self.ensure(40);self.y+=8
        lines=wrap(text,252,10,'italic' if sub else 'normal')
        for line in lines:self.line(line,self.x,self.y,252,10,'italic' if sub else 'normal',align='left' if sub else 'center');self.y+=12
        self.y+=5
    def float(self,height,draw):
        if self.y+height>720:self.pending.append((height,draw))
        else:draw()
    def figure(self,caption,source):
        image=mpimg.imread(PAPER/source);h=252*image.shape[0]/image.shape[1]
        lines=wrap(caption,252,8);height=h+len(lines)*9+14
        def draw():
            axes=self.fig.add_axes([self.x/612,1-(self.y+h)/792,252/612,h/792]);axes.imshow(image);axes.axis('off');self.y+=h+4
            for line in lines:self.line(line,self.x,self.y,252,8);self.y+=9
            self.y+=10
        self.float(height,draw)
    def table(self,caption,rows):
        count=len(rows[0]);widths=([92]+[32]*5 if count==6 else [110]+[(252-110)/(count-1)]*(count-1));caps=wrap(caption,252,8)
        row_height=15;height=len(caps)*9+len(rows)*row_height+17
        def draw():
            for line in caps:self.line(line,self.x,self.y,252,8,align='center');self.y+=9
            self.y+=4
            self.rule(self.y);self.y+=3
            for i,row in enumerate(rows):
                x=self.x
                for cell,w in zip(row,widths):self.line(cell,x+2,self.y,w-4,7.4,'bold' if i==0 else 'normal',align='left' if x==self.x else 'center');x+=w
                self.y+=row_height
                if i==0:self.rule(self.y-2)
            self.rule(self.y-2);self.y+=10
        self.float(height,draw)
    def rule(self,y):
        self.fig.add_artist(plt.Line2D([self.x/612,(self.x+252)/612],[1-y/792]*2,color='black',lw=.45,transform=self.fig.transFigure))
    def finish(self):
        while self.pending:self.next_column()
        # Balance a final text-only reference page at a reference boundary.
        if self.col==0 and self.page_no>1 and not self.fig.axes:
            candidates=[c['y'] for c in self.line_calls if re.match(r'^\[\d+\]',c['text'])]
            if len(candidates)>1:
                midpoint=(self.top+self.y)/2
                cutoff=min(candidates[1:],key=lambda y:abs(y-midpoint))
                for artist in self.fig.texts:
                    if getattr(artist,'_paper_y',0)>=cutoff:
                        x,y=artist.get_position();artist.set_position((x+270/612,y+(cutoff-self.top)/792))
        self.pdf.savefig(self.fig);plt.close(self.fig);self.pdf.close()
        return self.page_no

def build_pdf(blocks):
    plt.rcParams.update({'pdf.fonttype':42,'ps.fonttype':42})
    pdf=ReadingPDF(PAPER/'Research_Paper_IEEE.pdf');caption=''
    for kind,*data in blocks:
        if kind=='heading':
            if data[0] not in ['Abstract','Index Terms']:pdf.heading(data[0].upper())
        elif kind=='subheading':pdf.heading(data[0],sub=True)
        elif kind=='paragraph':pdf.paragraph(data[0])
        elif kind=='abstract':pdf.paragraph('Abstract—'+data[0],size=9,style='bold',indent=False,space=9)
        elif kind=='keywords':pdf.paragraph('Index Terms—'+data[0],size=9,style='italic',indent=False,space=8)
        elif kind=='reference':pdf.paragraph(data[0],size=8,indent=False,space=5)
        elif kind=='table_caption':caption=data[0]
        elif kind=='table':pdf.table(caption,data[0])
        elif kind=='figure':pdf.figure(*data)
    return pdf.finish()

def main():
    blocks=parse();build_tex(blocks);build_docx(blocks);pages=build_pdf(blocks)
    result={'pages':pages,'paragraphs':sum(b[0] in ['paragraph','abstract'] for b in blocks),
            'figures':sum(b[0]=='figure' for b in blocks),'tables':sum(b[0]=='table' for b in blocks),
            'references':sum(b[0]=='reference' for b in blocks),
            'pdf_renderer':'Matplotlib embedded-font IEEE-style reading PDF; IEEEtran source provided separately',
            'docx':'OOXML, US Letter, two columns, Times New Roman'}
    (PAPER/'build_manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(result)

if __name__=='__main__':main()
