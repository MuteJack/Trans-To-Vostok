이것은 validation_refactor branch를 편집하면서 임시로 작성한 markdown입니다.
merge후 삭제되거나, 기존 docs에 병합될 수 있습니다.

WorkFlow for Local Environment:
0. Template 검사 (개발자용):
   1. check_required_cols.py Template:    required columns 검사 (Critical)
   2. check_duplicated.py Template:       중복된 대상이 있는지 검사 (Critical)
   3. check_whitespace_text Template:     parse와 whitespace가 다르게 처리된 게 있는지 검사 (Critical)
   4. check_deprecated.py Template:       Template에 parse에 없는게 있는지 (게임 업데이트로 인해 unique id 등이 바뀌어서) 검사 (Warn)
   5. check_missing.py Template:          Template에 parse에 있는게 없는지 검사 (Info)
1. 번역 수정:
   1. tsv to xlsx
   2. 사람이 편집: xlsx 수정
   3. xlsx to tsv (필수)
2. locale의 source 검사:
   1. check_required_cols.py locale:      required columns 검사 (Critical)
   2. check_duplicates.py locale:         중복된 대상이 있는지 검사 (Critical)
   3. check_whitespace_text locale:       parse와 whitespace가 다르게 처리된 게 있는지 검사 (Critical)
   4. check_diff_with_Template locale:    Template와 현재 locale 사이에 다른 행이 있는지 검사
   5. check_deprecated.py locale:         parse에 없는게 있는지 (게임 업데이트로 인해 unique id 등이 바뀌어서) 검사
   6. check_missing.py locale:            parse에 있는게 없는지 검사
3. 번역 품질 검사:
   1. check_whitespace_translated:   text와 translation열 사이에 WhiteSpace 차이 검사
   2. Translation Conflic 검사 (같은 text지만 다른 번역)
4. 모드 빌드:

입력 인수: locale
 - locale 이름: 그 locale에 대해서
 - template: template에 대해서
 - all: enable된 locale들에 한해 각각
