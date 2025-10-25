# cli.py
import argparse
from extractor.extractor import ResumeExtractor
from extractor.utils import iter_files
from eval.evaluator import evaluate_pair
from pathlib import Path
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["extract","evaluate","batch_extract"], required=True)
    parser.add_argument("--input", required=True, help="file path or directory")
    parser.add_argument("--gt", help="ground truth .txt file (for evaluate mode)")
    parser.add_argument("--out", help="output file to save extracted text (json lines)")

    args = parser.parse_args()
    extractor = ResumeExtractor()
    if args.mode == "extract":
        res = extractor.extract(args.input)
        print(res.text[:2000])
    elif args.mode == "batch_extract":
        out_path = args.out or "extracted.jsonl"
        with open(out_path, "w", encoding="utf8") as fo:
            for f in iter_files(args.input):
                try:
                    r = extractor.extract(f)
                    fo.write(json.dumps({"source": r.source, "text": r.text[:], "pages": r.pages}) + "\n")
                    print("OK", f)
                except Exception as e:
                    print("ERR", f, e)
    elif args.mode == "evaluate":
        if not args.gt:
            raise SystemExit("Provide --gt ground truth file")
        # extract then evaluate
        r = extractor.extract(args.input)
        gt = Path(args.gt).read_text(encoding="utf8")
        metrics = evaluate_pair(gt, r.text)
        print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()
