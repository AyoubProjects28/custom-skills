#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, re, json, shutil, zipfile, tempfile, subprocess
from xml.sax.saxutils import escape as _xesc

PAR_RE = re.compile(r'<w:p\b(?:[^>]*?/>|.*?</w:p>)', re.S)
TXT_RE = re.compile(r'<w:t[^>]*>(.*?)</w:t>', re.S)

def xesc(s): return _xesc(s)
def unescape(s): return s.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
def para_text(p): return unescape(''.join(TXT_RE.findall(p)))
def first_rpr(p):
    m=re.search(r'<w:r\b[^>]*>\s*(<w:rPr>.*?</w:rPr>)',p,re.S)
    return m.group(1) if m else '<w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/></w:rPr>'
def ppr(p):
    m=re.search(r'<w:pPr>.*?</w:pPr>',p,re.S); return m.group(0) if m else ''
def p_attrs(p):
    m=re.match(r'<w:p\b([^>]*)>',p); return m.group(1) if m else ''

def apply_swap(xml, old, new):
    oe,ne=xesc(old),xesc(new)
    if oe in xml: return xml.replace(oe,ne), True
    for p in PAR_RE.findall(xml):
        if old in para_text(p):
            newtext=para_text(p).replace(old,new)
            rebuilt='<w:p%s>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'%(p_attrs(p),ppr(p),first_rpr(p),xesc(newtext))
            return xml.replace(p,rebuilt,1), True
    return xml, False

def remove_paras(xml, anchors, warnings):
    for a in anchors:
        hit=next((p for p in PAR_RE.findall(xml) if a in para_text(p)),None)
        if hit is None: warnings.append("remove not found: %r"%a[:40])
        else: xml=xml.replace(hit,'',1)
    return xml

def skill_para(label, body):
    rpr='<w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>%s</w:rPr>'
    return ('<w:p w:rsidR="003A0EE6" w:rsidRDefault="00000000">'
            '<w:pPr><w:spacing w:before="10" w:line="220" w:lineRule="auto"/><w:ind w:left="160"/><w:jc w:val="both"/></w:pPr>'
            '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>'
            '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            %(rpr%'<w:b/><w:bCs/>',xesc(label),rpr%'',xesc(body)))

def add_after(xml, items, warnings):
    last={}
    for it in items:
        anchor=it['anchor']; ref_block=last.get(anchor)
        if ref_block is None:
            ref_block=next((p for p in PAR_RE.findall(xml) if anchor in para_text(p)),None)
        if ref_block is None:
            warnings.append("add anchor not found: %r"%anchor[:40]); continue
        newp=skill_para(it.get('label',''),it.get('body',''))
        xml=xml.replace(ref_block,ref_block+newp,1); last[anchor]=newp
    return xml

def reorder_block(xml, anchors, warnings):
    blocks=[]
    for a in anchors:
        hit=next((p for p in PAR_RE.findall(xml) if a in para_text(p)),None)
        if hit is None: warnings.append("reorder anchor not found: %r"%a[:40]); return xml
        blocks.append(hit)
    positions=sorted(range(len(blocks)),key=lambda i: xml.index(blocks[i]))
    old_block=''.join(blocks[i] for i in positions)
    if old_block not in xml: warnings.append("reorder: bullets not contiguous; skipped"); return xml
    return xml.replace(old_block, ''.join(blocks), 1)

def trailing_empty(xml):
    for p in reversed(PAR_RE.findall(xml)):
        if para_text(p).strip()=='': return p
    return None

def repackage(srcdir, out_docx):
    os.makedirs(os.path.dirname(out_docx),exist_ok=True)
    if os.path.exists(out_docx):
        try: os.remove(out_docx)
        except OSError: pass
    with zipfile.ZipFile(out_docx,'w',zipfile.ZIP_DEFLATED) as z:
        for root,_,files in os.walk(srcdir):
            for fn in files:
                full=os.path.join(root,fn); z.write(full,os.path.relpath(full,srcdir))

def render_pdf(docx_path):
    outdir=os.path.dirname(docx_path)
    soffice=shutil.which('libreoffice') or shutil.which('soffice')
    if not soffice: return None,None
    subprocess.run([soffice,'--headless','--convert-to','pdf','--outdir',outdir,docx_path],
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=120)
    pdf=os.path.splitext(docx_path)[0]+'.pdf'
    if not os.path.exists(pdf): return None,None
    pages=None
    if shutil.which('pdfinfo'):
        r=subprocess.run(['pdfinfo',pdf],capture_output=True,text=True)
        m=re.search(r'Pages:\s+(\d+)',r.stdout)
        if m: pages=int(m.group(1))
    return pdf,pages

def page2_text(pdf):
    if not shutil.which('pdftotext'): return ''
    r=subprocess.run(['pdftotext','-f','2','-l','2',pdf,'-'],capture_output=True,text=True)
    return ' '.join(r.stdout.split())[:300]

def main():
    plan=json.load(open(sys.argv[1],encoding='utf-8'))
    ref,out=plan['reference'],plan['output']; warnings=[]
    if not zipfile.is_zipfile(ref):
        print(json.dumps({"error":"reference is not a valid .docx (open in Word? corrupted?): %s"%ref})); sys.exit(2)
    tmp=tempfile.mkdtemp()
    with zipfile.ZipFile(ref) as z: z.extractall(tmp)
    docpath=os.path.join(tmp,'word','document.xml')
    xml=open(docpath,encoding='utf-8').read()
    for s in plan.get('swaps',[]):
        xml,ok=apply_swap(xml,s['old'],s['new'])
        if not ok: warnings.append("swap not found: %r"%s['old'][:45])
    xml=remove_paras(xml,plan.get('remove',[]),warnings)
    xml=add_after(xml,plan.get('add_after',[]),warnings)
    if plan.get('reorder',{}).get('block'):
        xml=reorder_block(xml,plan['reorder']['block'],warnings)
    open(docpath,'w',encoding='utf-8').write(xml); repackage(tmp,out)
    result={"docx":out,"warnings":warnings}
    if plan.get('pdf',True):
        pdf,pages=render_pdf(out); result["pdf"]=pdf; result["pages"]=pages
        maxp=plan.get('max_pages',1); guard=0
        while pages and pages>maxp and guard<6:
            te=trailing_empty(xml)
            if not te: break
            xml=xml.replace(te,'',1); open(docpath,'w',encoding='utf-8').write(xml); repackage(tmp,out)
            pdf,pages=render_pdf(out); result["pdf"],result["pages"]=pdf,pages; guard+=1
        if pages and pages>maxp:
            result["page2"]=page2_text(pdf); result["overflow"]=True
    shutil.rmtree(tmp,ignore_errors=True)
    print(json.dumps(result,ensure_ascii