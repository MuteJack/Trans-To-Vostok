이것은 validation_refactor branch를 편집하면서 임시로 작성한 markdown입니다.
merge후 삭제되거나, 기존 docs에 병합될 수 있습니다.

WorkFlow for Local Environment:
0. Template 검사 (개발자용):
tools/validate_Template.py
   인자 없음 (Template 고정). 단계들을 순차 실행하고 결과를 종합해 overall severity 보고.
   1. required columns 검사 (Critical)
   tools/validation/check_required_cols.py Template:
   2. 중복된 대상이 있는지 검사 (Critical)
   tools/validation/check_duplicates.py Template:
   3. parse와 whitespace가 다르게 처리된 게 있는지 검사 (Critical)
   tools/validation/check_whitespace_text.py Template:  
   4. Template에 parse에 없는게 있는지 (게임 업데이트로 인해 unique id 등이 바뀌어서) 검사 (Warn)
   tools/validation/check_deprecated.py Template:
   5. Template에 parse에 있는게 없는지 검사 (Info)
   tools/validation/check_missing.py Template:
   6. flag 컬럼 (untranslatable 등) 값 정합성 검사 (Critical)
   tools/validation/check_flag.py Template:
   7. method 값 + method-종속 필드 조합 검사 (Critical)
   tools/validation/check_method.py Template:
   8. runtime 검증 (Critical)
      1. tools/build/build_runtime_tsv.py Template --ignore:    runtime TSV 생성.
         추가 옵션: --soft / --hard (기본) / --ignore (validate_xlsx 단계 생략), 
         --dry-run (Template 은 자동; .tmp/temp_build/Trans To Vostok/Template/runtime_tsv/ 에 출력)
      2. tools/build/check_runtime_tsv_conflict.py Template:
      위 단계의 출력에 대해 runtime matching key 충돌 검사
         추가 옵션: --dry-run (Template 은 자동; .tmp/temp_build/Trans To Vostok/Template/runtime_tsv/)

1. 번역 수정:
사람에 의해 진행
   1. canonical tsv파일을 xlsx로 빌드
   tools/rebuild_xlsx_new.py locale
      1. tools/translation/rebuild_translation_xlsx.py locale:
      2. tools/translation/rebuild_texture_xlsx.py locale:
   2. 사람이 편집:
   xlsx 파일 수정
   3. 수정된 xlsx를 canonical tsv로 변환 (필수)
   tools/build_canonical_tsv.py locale
      1. tools/translation/build_translation_tsv.py locale: 
      2. tools/translation/build_texture_tsv.py locale:

2. locale의 source 검사:
tools/validate_translation.py
   1. locale의 source 검사:
      1. required columns 검사 (Critical) :
      tools/validation/check_required_cols.py locale
      2. 중복된 대상이 있는지 검사 (Critical) :
      tools/validation/check_duplicates.py locale
      3. parse와 whitespace가 다르게 처리된 게 있는지 검사 (Critical) :
      tools/validation/check_whitespace_text locale
      4. Template와 현재 locale 사이의 차이 검사 :
      tools/validation/check_diff_with_Template.py locale
       - STRUCTURAL_DRIFT (Critical): 매칭 row 의 컬럼 값 다름
       - MISSING_IN_LOCALE / MISSING_SHEET (Warn): Template 에 있고 locale 에 없음
       - ORPHAN_IN_LOCALE / ORPHAN_SHEET (Info): locale 에만 있음
      5. parse에 없는게 있는지 (게임 업데이트로 인해 unique id 등이 바뀌어서) 검사 (Warn)
      tools/validation/check_deprecated.py locale:
      6. parse에 있는게 없는지 검사 (Info) :
      tools/validation/check_missing.py locale
   2. 번역 품질 검사:
      1. text와 translation열 사이에 WhiteSpace 차이 검사
      tools/validation/check_whitespace_translated.py locale:
      2. 같은 text지만 다른 번역을 사용한 부분 검사
      tools/validation/check_conflict.py locale
   3. runtime 검사
      1. runtime tsv를 .tmp/temp_build/Trans To Vostok/{locale}/runtime_tsv/에 빌드
      tools/build/build_runtime_tsv.py locale --dry-run
      2. .tmp/temp_build/Trans To Vostok/{locale}/runtime_tsv/ 의 tsv파일을 검증
      tools/build/check_runtime_tsv_conflict.py locale --dry-run
3. 모드 빌드:
   tools/build_mod_package_new.py locale
   1. runtime_tsv 빌드 :
   (/Trans To Vostok/{locale}/runtime_tsv/)
      1. tools/build/build_runtime_tsv.py locale
      2. tools/build/check_runtime_tsv_conflict.py locale
   2. 메타데이터 생성 (per locale):
   (/Trans To Vostok/{locale}/)
      1. tools/build/get_texture_credits.py locale
      2. tools/build/build_attributions.py  locale
      3. tools/build/build_translation_credit.py locale
      4. tools/build/build_texture_meta.py locale
   3. 메타데이터 생성 (global)
   (/Trans To Vostok/)
      1. tools/build/build_authors.py
      global(모든 언어에 대해서)이므로, locale 인수를 받지 않음
      2. tools/build/build_mod_info.py
      global(모든 언어에 대해서)이므로, locale 인수를 받지 않음
   4. 패키징 (tools/build/pack_mod_zip.py)
   ZIP 생성 → Trans To Vostok.zip

입력 인수: locale
 - locale 이름: 그 locale에 대해서
 - template: template에 대해서
 - all: enable된 locale들에 한해 각각
