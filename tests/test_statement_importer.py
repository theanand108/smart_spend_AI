from src.statement_importer import parse_google_pay_text, parse_phonepe_csv


PHONEPE_SAMPLE = '''Transaction Statement for 6307183070
Duration,"30 Jul, 2026 - 29 Aug, 2026"

Date,Time,Transaction Details,Transaction ID,UTR,Transaction Type,Credit/debit instrument,Amount
"Aug 29, 2026","12:30 am","Paid to Vishal Bhai 2","T2608290030197862671909","653919911522","DEBIT","Paid by XXXXXXX1831","100"
"Aug 26, 2026","09:00 am","Received from MUKUND KUSHWAHA","T2608260900463826377542","660440391566","CREDIT","Credited to XXXXXXX1831","5000"
"Aug 25, 2026","03:31 pm","Paid to Anand bank","T2608251531164719873160","515202082686","DEBIT","Paid by XXXXXXX1831","299"
'''


GPAY_SAMPLE = '''Transaction statement
Date & time Transaction details Amount
01 Jul, 2026
02:20 PM
Paid to mukund Kushwaha
UPI Transaction ID: 618266600033
Paid by Uttar Pradesh Gramin Bank 2909
₹1,000
01 Jul, 2026
04:09 PM
Paid to EKART
UPI Transaction ID: 654883594580
Paid by Uttar Pradesh Gramin Bank 2909
₹369
02 Jul, 2026
05:00 PM
Received from MUKUND KUSHWAHA
UPI Transaction ID: 999999999999
Received by Uttar Pradesh Gramin Bank 2909
₹2,500
'''


def test_phonepe_csv_normalizes_debits_and_credits():
    result = parse_phonepe_csv(PHONEPE_SAMPLE)

    assert len(result.transactions) == 3
    assert len(result.expenses) == 2
    assert len(result.received) == 1

    assert result.expenses[0].merchant_name == "Vishal Bhai 2"
    assert result.expenses[0].amount == 100
    assert result.expenses[0].source_transaction_id == "T2608290030197862671909"
    assert result.expenses[0].note == "Paid to Vishal Bhai 2"

    assert result.received[0].merchant_name == "MUKUND KUSHWAHA"
    assert result.received[0].amount == 5000
    assert result.received[0].source_transaction_id == "T2608260900463826377542"
    assert result.received[0].note == "Received from MUKUND KUSHWAHA"


def test_google_pay_pdf_text_normalizes_paid_and_received_transactions():
    result = parse_google_pay_text(GPAY_SAMPLE)

    assert len(result.transactions) == 3
    assert len(result.expenses) == 2
    assert len(result.received) == 1

    assert result.expenses[0].merchant_name == "mukund Kushwaha"
    assert result.expenses[0].amount == 1000
    assert result.expenses[0].source_transaction_id == "618266600033"
    assert result.expenses[0].note == "Paid to mukund Kushwaha"

    assert result.expenses[1].merchant_name == "EKART"
    assert result.expenses[1].note == "Paid to EKART"
    assert result.received[0].merchant_name == "MUKUND KUSHWAHA"
    assert result.received[0].amount == 2500
    assert result.received[0].note == "Received from MUKUND KUSHWAHA"


def test_gpay_converted_flat_csv_is_not_treated_as_a_supported_transaction_table():
    converted_csv = '''"Transactionstatement"\n"01Jul,2026"\n"02:20PM"\n"Paidto","EKART"\n"UPITransaction","ID:654883594580"\n"₹369"\n'''

    try:
        parse_phonepe_csv(converted_csv)
    except ValueError as exc:
        assert "header" in str(exc).lower()
    else:
        raise AssertionError("A flattened PDF-to-CSV file should not be accepted as a structured CSV.")
