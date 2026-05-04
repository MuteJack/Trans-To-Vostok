1. Visit: https://github.com/bruvzg/gdsdecomp/releases
2. Download: windows-vN.N.N.zip
3. Extract gdre_tools.exe to: %~dp03rd_party\gdre_tools\
4. Execute gdre_tools.exe to extract .pck file
   For Example,

```powershell
cd {Road to Vostok Dir}/Trans to Vostok
3rd_party\gdre_tools\gdre_tools.exe" ^
    --headless ^
    --recover="%~dp0..\..\..\RTV.pck" ^
    --output="%~dp0..\.tmp\pck_recovered" ^
    --bytecode=4.6.1
```

5. Make sure that

보안 위협 방지를 위해, 번역 파일(xlsx)에 다음이 포함된 Push/Merge 요청은 거절될 수 있습니다.
- Excel 파일
- Excel(xlsx) 파일 내에 VBA(Visual Basic for Application) 매크로를 사용/포함하는 행위
- Excel(xlsx) 파일의 확장자를 매크로 실행이 가능한 확장자(xlsm 등)로 변경하는 행위
- Excel(xlsx) 파일 내에 링크, 또는 하이퍼링크를 포함하는 행위
- Excel(xlsx) 파일 내의 데이터가 임배디드 객체, DDE, 데이터 연결 등, 외부의 데이터와 연결하도록 하는 행위

보안 위협 방지를 위해
- python(.py), godot(.gd) 스크립트 등에서 

저작권 문제를 방지하기 위해, 다음이 포함된 Push/Merge 요청은 거절될 수 있습니다.

- 이미지 파일을 직접 수정하는 행위는 보안 위협 방지 등을 위해, 대부분의 경우 개발자가 직접 수정할 수 있습니다. 이미지 내의 텍스트에 대한 번역 수정 요청은 가급적 Issue에 등록해주세요.
- 외부 이미지 소스가 포함되어 있는, 편집 가능한 파일(예: Adobe Photoshop/Illustrator 파일)을 포함하는 행위.
- 
