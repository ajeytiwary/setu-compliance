"""Generate clearly synthetic PDF fixtures for the pilot dossier."""
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'demo_dossier'
ROOT.mkdir(parents=True, exist_ok=True)
COMMON = [
    'SYNTHETIC DEMONSTRATION DOCUMENT - NOT VALID FOR CUSTOMS OR CBAM FILING',
    'Demo shipment: DEMO-EU-STEEL-2026-001',
    'Exporter: DEMO STEEL INDIA PRIVATE LIMITED',
    'Importer: DEMO EU METALS NV, Belgium',
    'Invoice Number: DEMO-EXP-2026-001',
    'Purchase Order: DEMO-PO-102833',
    'Origin Country: IN',
    'Destination Country: BE',
    'HS/CN Code: 72221119',
    'Net Weight KG: 2252.00',
    'Container Number: DEMU1234560',
]
DOCS = {
 'invoice_initial': ['Document Type: INVOICE','Invoice Date: 2026-09-15','Currency: EUR','Invoice Value: 45000.00','Heat Number: DEMO-HEAT-20376','Coil Number: DEMO-COIL-27792','ROW 1 | CN 72221119 | HEAT DEMO-HEAT-20376 | COIL DEMO-COIL-27792 | KG 2252.00 | EUR 45000.00'],
 'packing_initial': ['Document Type: PACKING_LIST','Heat Number: DEMO-HEAT-20376','Coil Number: DEMO-COIL-27792','Gross Weight KG: 2320.00','Packages: 4','ROW 1 | COIL DEMO-COIL-27792 | HEAT DEMO-HEAT-20376 | KG 2252.00 | PACKAGES 4'],
 'shipping_initial': ['Document Type: SHIPPING_BILL','Shipping Bill Number: DEMO-SB-4240917','Shipping Date: 2026-09-16','Container Number: DEMU1234560','ROW 1 | CN 72221119 | KG 2252.00 | EUR 45000.00'],
 'bl_initial': ['Document Type: BILL_OF_LADING','Bill Of Lading: DEMO-BL-SLDH0001','On Board Date: 2026-09-18','Port Of Loading: MUNDRA','Port Of Discharge: ANTWERP','Gross Weight KG: 2320.00','Packages: 4'],
 'mtc_initial': ['Document Type: MTC','Certificate Number: DEMO-MTC-3.1-001','Certificate Standard: EN 10204 3.1','Heat Number: DEMO-HEAT-WRONG','Coil Number: DEMO-COIL-27792','Manufacturer: DEMO STEEL INDIA PRIVATE LIMITED','ROW 1 | HEAT DEMO-HEAT-WRONG | COIL DEMO-COIL-27792 | KG 2252.00'],
 'sad_initial': ['Document Type: SAD','MRN: DEMO26BE000000001','EORI: BEDEMO000001','Declaration Date: 2026-09-29','Bill Of Lading: DEMO-BL-SLDH0001','Customs Value EUR: 45000.00','ROW 1 | CN 72221119 | KG 2252.00 | EUR 45000.00'],
 'cbam_initial': ['Document Type: CBAM_INSTALLATION','Installation ID: DEMO-INSTALL-001','Reporting Period: 2026','Production Route: EAF','Activity Level T: 1000.00','Direct Emissions TCO2: 1500.00','Precursor Quantity T: 100.00','Precursor SEE TCO2/T: 0.50','Verifier Status: UNVERIFIED','Monitoring Plan Ref: DEMO-MP-2026'],
 'mtc_corrected': ['Document Type: MTC','Certificate Number: DEMO-MTC-3.1-002','Certificate Standard: EN 10204 3.1','Heat Number: DEMO-HEAT-20376','Coil Number: DEMO-COIL-27792','Manufacturer: DEMO STEEL INDIA PRIVATE LIMITED','ROW 1 | HEAT DEMO-HEAT-20376 | COIL DEMO-COIL-27792 | KG 2252.00'],
 'cbam_corrected': ['Document Type: CBAM_INSTALLATION','Installation ID: DEMO-INSTALL-001','Reporting Period: 2026','Production Route: EAF','Activity Level T: 1000.00','Direct Emissions TCO2: 1500.00','Precursor Quantity T: 100.00','Precursor SEE TCO2/T: 0.50','Verifier Status: VERIFIED','Verifier Report Ref: DEMO-VER-2026-001','Monitoring Plan Ref: DEMO-MP-2026'],
}


def build_pdf(lines):
    writer = PdfWriter(); page = writer.add_blank_page(width=595, height=842)
    regular = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    bold = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica-Bold')})
    fonts = DictionaryObject({NameObject('/F1'): writer._add_object(regular), NameObject('/F2'): writer._add_object(bold)})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): fonts})
    doc_type = next(line.split(': ',1)[1] for line in lines if line.startswith('Document Type: '))
    display = [line for line in lines[1:] if not line.startswith('Document Type: ')]
    display.insert(0, 'Document Type: ' + doc_type)
    commands = ['0.07 0.18 0.23 rg','0 742 595 100 re f',
                '0.78 0.88 0.86 rg','45 721 505 1 re f',
                '0.97 0.70 0.28 rg']
    def label(text,x,y,size=10,font='F1',color='0.07 0.18 0.23 rg'):
        safe=text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        return [color,'BT',f'/{font} {size} Tf',f'1 0 0 1 {x} {y} Tm',f'({safe}) Tj','ET']
    commands += label('EUROSETU  /  PILOT EVIDENCE DOSSIER',45,817,10,'F2','1 1 1 rg')
    commands += label(doc_type.replace('_',' '),45,781,21,'F2','1 1 1 rg')
    commands += label(lines[0],45,752,9,'F2','1 0.79 0.40 rg')
    y=696
    for line in display:
        if line.startswith('ROW '):
            commands += ['0.92 0.96 0.96 rg',f'40 {y-7} 515 21 re f']
            commands += label(line,47,y,9,'F1')
        else:
            commands += label(line,45,y,10,'F2' if line.startswith(('Invoice Number:','Certificate Number:','Bill Of Lading:','MRN:','Installation ID:')) else 'F1')
        y-=23
    commands += label('Generated for product demonstration. All names and identifiers are fictitious.',45,38,8,'F1','0.4 0.46 0.49 rg')
    stream = DecodedStreamObject(); stream.set_data(('\n'.join(commands)+'\n').encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.add_metadata({'/Title': 'SYNTHETIC DEMONSTRATION DOCUMENT', '/Subject': 'EuroSetu pilot fixture - not real shipment evidence'})
    from io import BytesIO
    buf=BytesIO(); writer.write(buf); return buf.getvalue()


if __name__ == '__main__':
    import hashlib
    import json
    manifest={"synthetic_demonstration": True,
              "notice": "Fictitious evidence; not valid for customs or CBAM filing",
              "shipment_ref": "DEMO-EU-STEEL-2026-001", "documents": []}
    for name, body in DOCS.items():
        data=build_pdf(COMMON + body)
        (ROOT / f'{name}.pdf').write_bytes(data)
        manifest["documents"].append({"filename": f"{name}.pdf", "sha256": hashlib.sha256(data).hexdigest(),
                                      "role": next(line.split(": ",1)[1] for line in body if line.startswith("Document Type: ")),
                                      "version": 2 if name.endswith("corrected") else 1})
        print(name, len(data))
    (ROOT / "manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
