Attribute VB_Name = "Module"
Private Declare Function URLDownloadToFile _
    Lib "urlmon" Alias "URLDownloadToFileA" _
    (ByVal pCaller As Long, _
    ByVal szURL As String, _
    ByVal szFileName As String, _
    ByVal dwReserved As Long, _
    ByVal lpfnCB As Long) As Long
 
Private Declare Function DeleteUrlCacheEntry _
    Lib "wininet" Alias "DeleteUrlCacheEntryA" _
    (ByVal lpszUrlName As String) As Long

Type BaseInfo
    initial_date As Date
    grid_num As Variant
    x_num As Variant
    y_num As Variant
    s_lat As Variant
    s_lon As Variant
    e_lat As Variant
    e_lon As Variant
    d_lat As Variant
    d_lon As Variant
End Type

Type SwiGrib2
    base_info As BaseInfo
    swi As Variant
    first_tunk As Variant
    second_tunk As Variant
End Type

Type SwiTimeSeries
    ft As Integer
    value As Variant
End Type

Type GuidanceTimeSeries
    ft As Integer
    value As Variant
End Type

Type Risk
    ft As Integer
    value As Integer
End Type

Type GuidanceGrib2
    base_info As BaseInfo
    data() As GuidanceTimeSeries
End Type

Type Mesh
    area_name As String
    code As String
    lon As Double
    lat As Double
    x As Integer
    y As Integer
    advisary_bound As Integer
    warning_bound As Integer
    dosyakei_bound As Integer
    swi() As SwiTimeSeries
    rain() As GuidanceTimeSeries
End Type

Type Area
    name As String
    meshes() As Mesh
    risk_timeline() As Risk
End Type
   
Public Type Prefecture
    name As String
    code As String
    areas() As Area
    area_min_x As Integer
    area_max_y As Integer
End Type

Sub main_process(initial)
    Application.ScreenUpdating = False

    'initial = DateSerial(2023, 6, 1) + TimeSerial(12, 0, 0)
    
    swi_url = "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/swi10/" & Format(initial, "yyyy/mm/dd/") & "Z__C_RJTD_" & Format(initial, "yyyymmddhhnnss") & "_SRF_GPV_Ggis1km_Psw_Aper10min_ANAL_grib2.bin"
    guidance_url = "http://lunar1.fcd.naps.kishou.go.jp/srf/Grib2/Rtn/gdc/" & Format(initial, "yyyy/mm/dd/") & "guid_msm_grib2_" & Format(initial, "yyyymmddhhnnss") & "_rmax0" & Hour(initial) Mod 6 & ".bin"
    
    swi_filename = "swi_grib2.bin"
    guidance_filename = "guidance_grib2.bin"
    
    swi_filename = download(swi_url, swi_filename)
    guidance_filename = download(guidance_url, guidance_filename)

    Dim prefectures() As Prefecture
        
    prefectures = calc_data(swi_filename, guidance_filename)
    Call draw_data(prefectures)
    
    Call prepare_map(prefectures, initial)
    
    Application.ScreenUpdating = True
End Sub


Function download(url, filename)
    'ファイルをダウンロードするサブルーチン

    current_dir = ThisWorkbook.Path
    file_path = current_dir & "/" & filename

    Dim FSO As Object
    Set FSO = CreateObject("Scripting.FileSystemObject")

    'ファイルが存在する場合は削除しておく
    If dir(file_path) <> "" Then
        FSO.GetFile(file_path).Delete
    End If

    '// キャッシュクリア
    Call DeleteUrlCacheEntry(url)
    
    '// ダウンロード
    ret = URLDownloadToFile(0, url, file_path, 0, 0)
    
    download = file_path
End Function

Function calc_data(swi_filename, guidance_filename) As Prefecture()
    Dim swi_grib2 As SwiGrib2
    Dim guidance_grib2 As GuidanceGrib2
    Dim prefectures() As Prefecture

    swi_grib2 = unpack_swi_grib2(swi_filename)
    guidance_grib2 = unpack_guidance_grib2(guidance_filename)
    prefectures = prepare_areas()
    
    For i = 1 To UBound(prefectures)
        For j = 1 To UBound(prefectures(i).areas)
            For k = 1 To UBound(prefectures(i).areas(j).meshes)
                prefectures(i).areas(j).meshes(k).swi = calc_swi_timelapse(prefectures(i).areas(j).meshes(k), swi_grib2, guidance_grib2)
                prefectures(i).areas(j).meshes(k).rain = calc_rain_timelapse(prefectures(i).areas(j).meshes(k), guidance_grib2)
            Next k
            prefectures(i).areas(j).risk_timeline = calc_risk_timeline(prefectures(i).areas(j).meshes)
        Next j
    Next i
    
    
    calc_data = prefectures
End Function

Sub draw_data(prefectures() As Prefecture)
    For p = 1 To UBound(prefectures)
        
        Worksheets(prefectures(p).code + "_timeline").Cells.Clear
        Worksheets(prefectures(p).code + "_swi").Cells.Clear
        Worksheets(prefectures(p).code + "_rain").Cells.Clear
        For i = 1 To UBound(prefectures(p).areas(1).risk_timeline)
            Worksheets(prefectures(p).code + "_timeline").Cells(1, i + 1) = prefectures(p).areas(1).risk_timeline(i).ft
        Next i
        
        
        
        l = 2
        For i = 1 To UBound(prefectures(p).areas)
            Worksheets(prefectures(p).code + "_swi").Cells(1, 1) = prefectures(p).area_min_x
            Worksheets(prefectures(p).code + "_swi").Cells(1, 2) = prefectures(p).area_max_y
            For j = 1 To UBound(prefectures(p).areas(i).meshes)
                Worksheets(prefectures(p).code + "_swi").Cells(l, 1) = prefectures(p).areas(i).name

                Worksheets(prefectures(p).code + "_swi").Cells(l, 2) = prefectures(p).areas(i).meshes(j).x
                Worksheets(prefectures(p).code + "_swi").Cells(l, 3) = prefectures(p).areas(i).meshes(j).y
                Worksheets(prefectures(p).code + "_swi").Cells(l, 4) = prefectures(p).areas(i).meshes(j).advisary_bound
                Worksheets(prefectures(p).code + "_swi").Cells(l, 5) = prefectures(p).areas(i).meshes(j).warning_bound
                Worksheets(prefectures(p).code + "_swi").Cells(l, 6) = prefectures(p).areas(i).meshes(j).dosyakei_bound
                
                For k = 1 To UBound(prefectures(p).areas(i).meshes(j).swi)
                    Worksheets(prefectures(p).code + "_swi").Cells(l, k + 6) = prefectures(p).areas(i).meshes(j).swi(k).value
                Next k
                
                Worksheets(prefectures(p).code + "_rain").Cells(l, 1) = prefectures(p).areas(i).name
                Worksheets(prefectures(p).code + "_rain").Cells(l, 2) = prefectures(p).areas(i).meshes(j).x
                Worksheets(prefectures(p).code + "_rain").Cells(l, 3) = prefectures(p).areas(i).meshes(j).y
                For k = 1 To UBound(prefectures(p).areas(i).meshes(j).rain)
                    Worksheets(prefectures(p).code + "_rain").Cells(l, k + 3) = prefectures(p).areas(i).meshes(j).rain(k).value
                Next k
                
                l = l + 1
            Next j
            
            Worksheets(prefectures(p).code + "_timeline").Cells(i + 1, 1) = prefectures(p).areas(i).name
            
            For j = 1 To UBound(prefectures(p).areas(i).risk_timeline)
                level = prefectures(p).areas(i).risk_timeline(j).value
                If level = 1 Then
                    Worksheets(prefectures(p).code + "_timeline").Cells(i + 1, j + 1).Interior.ColorIndex = 6
                ElseIf level = 2 Then
                    Worksheets(prefectures(p).code + "_timeline").Cells(i + 1, j + 1).Interior.ColorIndex = 3
                ElseIf level = 3 Then
                    Worksheets(prefectures(p).code + "_timeline").Cells(i + 1, j + 1).Interior.ColorIndex = 21
                Else
                    Worksheets(prefectures(p).code + "_timeline").Cells(i + 1, j + 1).Interior.ColorIndex = 15
                End If
            
            Next j
        Next i
    Next p
End Sub

Sub prepare_map(prefectures() As Prefecture, initial)
    Dim sheet As Worksheet
    
    For i = 1 To UBound(prefectures)
        x_max = 1
        y_max = 1
        Set sheet = Worksheets(prefectures(i).code + "_map")
        sheet.Cells.Clear
        sheet.Cells.ColumnWidth = 0.6
        sheet.Cells.RowHeight = 4
        sheet.Range("1:1").RowHeight = 30
        sheet.Range("A1:X1").Merge
        sheet.Range("Y1:AD1").Merge
        
        For j = 1 To UBound(prefectures(i).areas)
            For k = 1 To UBound(prefectures(i).areas(j).meshes)
                x = prefectures(i).areas(j).meshes(k).x - prefectures(i).area_min_x + 1
                y = prefectures(i).area_max_y - prefectures(i).areas(j).meshes(k).y + 1
                sheet.Cells(y + 1, x + 1) = prefectures(i).areas(j).name
                x_max = WorksheetFunction.Max(x_max, x)
                y_max = WorksheetFunction.Max(y_max, y)
            Next k
        Next j
        For j = 2 To y_max + 1
            For k = 2 To y_max + 1
                If Not IsEmpty(sheet.Cells(j, k)) Then
                    If IsEmpty(sheet.Cells(j - 1, k)) Then
                        With sheet.Cells(j, k).Borders(xlEdgeTop)
                            .LineStyle = xlContinuous
                            .Weight = xlMedium
                        End With
                    ElseIf sheet.Cells(j, k) <> sheet.Cells(j - 1, k) Then
                        With sheet.Cells(j, k).Borders(xlEdgeTop)
                            .LineStyle = xlContinuous
                            .Weight = xlThin
                        End With
                    End If

                    If IsEmpty(sheet.Cells(j + 1, k)) Then
                        With sheet.Cells(j, k).Borders(xlEdgeBottom)
                            .LineStyle = xlContinuous
                            .Weight = xlMedium
                        End With
                    ElseIf sheet.Cells(j, k) <> sheet.Cells(j + 1, k) Then
                        With sheet.Cells(j, k).Borders(xlEdgeBottom)
                            .LineStyle = xlContinuous
                            .Weight = xlThin
                        End With
                    End If

                    If IsEmpty(sheet.Cells(j, k - 1)) Then
                        With sheet.Cells(j, k).Borders(xlEdgeLeft)
                            .LineStyle = xlContinuous
                            .Weight = xlMedium
                        End With
                    ElseIf sheet.Cells(j, k) <> sheet.Cells(j, k - 1) Then
                        With sheet.Cells(j, k).Borders(xlEdgeLeft)
                            .LineStyle = xlContinuous
                            .Weight = xlThin
                        End With
                    End If

                    If IsEmpty(sheet.Cells(j, k + 1)) Then
                        With sheet.Cells(j, k).Borders(xlEdgeRight)
                            .LineStyle = xlContinuous
                            .Weight = xlMedium
                        End With
                    ElseIf sheet.Cells(j, k) <> sheet.Cells(j, k + 1) Then
                        With sheet.Cells(j, k).Borders(xlEdgeRight)
                            .LineStyle = xlContinuous
                            .Weight = xlThin
                        End With
                    End If
                End If
            Next k
        Next j
        sheet.Cells.ClearContents
        sheet.Cells(1, 1) = Format(initial, "yyyy年mm月dd日 hh：nn") + " UTC"
        Call draw_map(prefectures(i).code, 0)
    Next i
End Sub

Sub draw_map(prefecture_code, ft)
    Application.ScreenUpdating = False
    Dim swi_sheet As Variant
    Dim map_sheet As Worksheet
    
    swi_sheet = Worksheets(prefecture_code + "_swi").UsedRange
    Set map_sheet = Worksheets(prefecture_code + "_map")
    If Worksheets(prefecture_code + "_swi").UsedRange.Columns.Count < 6 + ft / 3 + 1 Then
        Exit Sub
    End If
    
    map_sheet.Cells(1, 25) = "FT=" & ft
    
    min_x = swi_sheet(1, 1)
    max_y = swi_sheet(1, 2)
    
    For i = 2 To UBound(swi_sheet)
        x = swi_sheet(i, 2) - min_x + 2
        y = max_y - swi_sheet(i, 3) + 1
        advisary_bound = swi_sheet(i, 4)
        warning_bound = swi_sheet(i, 5)
        dosyakei_bound = swi_sheet(i, 6)
        value = swi_sheet(i, 7 + ft / 3)
        
        If value >= dosyakei_bound Then
            map_sheet.Cells(y + 1, x).Interior.ColorIndex = 21
        ElseIf value >= warning_bound Then
            map_sheet.Cells(y + 1, x).Interior.ColorIndex = 3
        ElseIf value >= advisary_bound Then
            map_sheet.Cells(y + 1, x).Interior.ColorIndex = 6
        Else
            map_sheet.Cells(y + 1, x).Interior.ColorIndex = 2
        End If
    Next i
    Application.ScreenUpdating = True
End Sub

Sub map_forward(prefecture_code)
    ft = Val(Mid(Worksheets(prefecture_code + "_map").Cells(1, 25), 4))
    If ft = 0 Then Exit Sub
    Call draw_map(prefecture_code, ft - 3)
End Sub

Sub map_back(prefecture_code)
    ft = Val(Mid(Worksheets(prefecture_code + "_map").Cells(1, 25), 4))
    Call draw_map(prefecture_code, ft + 3)
End Sub

Function calc_risk_timeline(meshes() As Mesh) As Risk()
    
    'メッシュごとの基準超過を集計して市町村ごとのタイムラインを作る
    Dim risk_timeline() As Risk
    ReDim risk_timeline(UBound(meshes(1).swi))
    
    For i = 1 To UBound(meshes(1).swi)
        risk_timeline(i).ft = meshes(1).swi(i).ft
        risk_timeline(i).value = 0
        For j = 1 To UBound(meshes)
        '土砂警危険度追加
            If meshes(j).swi(i).value >= meshes(j).dosyakei_bound Then
                risk_timeline(i).value = WorksheetFunction.Max(risk_timeline(i).value, 3)
            ElseIf meshes(j).swi(i).value >= meshes(j).warning_bound Then
                risk_timeline(i).value = WorksheetFunction.Max(risk_timeline(i).value, 2)
            ElseIf meshes(j).swi(i).value >= meshes(j).advisary_bound Then
                risk_timeline(i).value = WorksheetFunction.Max(risk_timeline(i).value, 1)
            End If
        Next j
    Next i
    calc_risk_timeline = risk_timeline
End Function


Function prepare_areas() As Prefecture()
    Dim prefectures(6) As Prefecture
    prefectures(1).code = "shiga": prefectures(1).name = "滋賀"
    prefectures(2).code = "kyoto": prefectures(2).name = "京都"
    prefectures(3).code = "osaka": prefectures(3).name = "大阪"
    prefectures(4).code = "hyogo": prefectures(4).name = "兵庫"
    prefectures(5).code = "nara": prefectures(5).name = "奈良"
    prefectures(6).code = "wakayama": prefectures(6).name = "和歌山"
    
    For i = 1 To UBound(prefectures)
        Dim areas() As Area
        With Worksheets("dosha_" + prefectures(i).code)
             bound_data = .Range(.Range("A3"), .Cells(.Rows.Count, 5).End(xlUp)).value
        End With
        
        With Worksheets("dosyakei_" + prefectures(i).code)
             dosyakei_bound_data = .Range(.Range("A1"), .Cells(.Rows.Count, 13).End(xlUp)).value
        End With
        
        Dim meshes() As Mesh
        ReDim meshes(UBound(bound_data))
        
        Dim dic As Object
        Set dic = CreateObject("Scripting.Dictionary")
        k = 1
        For j = 1 To UBound(bound_data)
            code = CStr(bound_data(j, 3))
            meshes(j).code = code
            c = meshcode_to_coordinate(meshes(j).code)
            meshes(j).lat = c(0)
            meshes(j).lon = c(1)
            
            meshes(j).dosyakei_bound = 9999
            
            For p = 1 To UBound(dosyakei_bound_data)
                If dosyakei_bound_data(p, 1) = code Then
                    b = dosyakei_bound_data(p, 13)
                    If b < 999 Then
                        meshes(j).dosyakei_bound = b
                    End If
                    Exit For
                End If
            Next p

            If bound_data(j, 4) = "－" Then
                meshes(j).advisary_bound = 9999
            Else
                meshes(j).advisary_bound = Val(bound_data(j, 4))
            End If
            If bound_data(j, 5) = "－" Then
                meshes(j).warning_bound = 9999
            Else
                meshes(j).warning_bound = Val(bound_data(j, 5))
            End If
            
            area_name = bound_data(j, 2)
            meshes(j).area_name = area_name
            
            If Not dic.Exists(area_name) Then
                dic.Add area_name, k
                k = k + 1
            End If
        Next j
        
        
        area_names = dic.Keys
        ReDim areas(UBound(area_names) + 1)
        For j = 1 To UBound(areas)
            areas(j).name = area_names(j - 1)
            ReDim areas(j).meshes(0)
        Next j
        
        'メッシュを市町村ごとに振り分け
        For j = 1 To UBound(meshes)
            area_num = dic.Item(meshes(j).area_name)
            ReDim Preserve areas(area_num).meshes(UBound(areas(area_num).meshes) + 1)
            areas(area_num).meshes(UBound(areas(area_num).meshes)) = meshes(j)
        Next j
        
        prefectures(i).areas = areas
    Next i
    
    'メッシュごとの緯度経度、および標準地域メッシュ上での座標を計算
    For i = 1 To UBound(prefectures)
        area_min_x = 9999
        area_max_y = 0
        For j = 1 To UBound(prefectures(i).areas)
            For k = 1 To UBound(prefectures(i).areas(j).meshes)
                Coordinate = meshcode_to_coordinate(prefectures(i).areas(j).meshes(k).code)
                prefectures(i).areas(j).meshes(k).lat = Coordinate(0)
                prefectures(i).areas(j).meshes(k).lon = Coordinate(1)
                index = meshcode_to_index(prefectures(i).areas(j).meshes(k).code)
                prefectures(i).areas(j).meshes(k).x = index(0)
                prefectures(i).areas(j).meshes(k).y = index(1)
                
                area_min_x = WorksheetFunction.Min(area_min_x, prefectures(i).areas(j).meshes(k).x)
                area_max_y = WorksheetFunction.Max(area_max_y, prefectures(i).areas(j).meshes(k).y)
            Next k
        Next j
        prefectures(i).area_min_x = area_min_x
        prefectures(i).area_max_y = area_max_y
    Next i
    
    prepare_areas = prefectures
    
End Function


Function calc_rain_timelapse(m As Mesh, guidance_grib2 As GuidanceGrib2) As GuidanceTimeSeries()
    Dim guidance_time_series As GuidanceTimeSeries
    guidance_index = get_data_num(m.lat, m.lon, guidance_grib2.base_info)
    Dim rain_timeseries() As GuidanceTimeSeries
    ReDim rain_timeseries(UBound(guidance_grib2.data))
    
    For i = 1 To UBound(guidance_grib2.data)
        rain_timeseries(i).ft = guidance_grib2.data(i).ft
        rain_timeseries(i).value = guidance_grib2.data(i).value(guidance_index)
    Next i
    calc_rain_timelapse = rain_timeseries
End Function

Function calc_swi_timelapse(m As Mesh, swi_grib2 As SwiGrib2, guidance_grib2 As GuidanceGrib2) As SwiTimeSeries()
    Dim guidance_time_series As GuidanceTimeSeries
    swi_index = get_data_num(m.lat, m.lon, swi_grib2.base_info)
    swi = swi_grib2.swi(swi_index) / 10
    first_tunk = swi_grib2.first_tunk(swi_index) / 10
    second_tunk = swi_grib2.second_tunk(swi_index) / 10
    third_tunk = swi - first_tunk - second_tunk

    guidance_index = get_data_num(m.lat, m.lon, guidance_grib2.base_info)
    
    Dim swi_time_siries() As SwiTimeSeries
    ReDim swi_time_siries(UBound(guidance_grib2.data) + 1)
    
    swi_time_siries(1).ft = 0
    swi_time_siries(1).value = swi
    
    tmp_f = 0
    tmp_s = 0
    tmp_t = 0
    For i = 1 To UBound(guidance_grib2.data)
       
        Call calc_tunk_model(first_tunk, second_tunk, third_tunk, 3, guidance_grib2.data(i).value(guidance_index), tmp_f, tmp_s, tmp_t)
        swi_time_siries(i + 1).ft = guidance_grib2.data(i).ft
        swi_time_siries(i + 1).value = tmp_f + tmp_s + tmp_t
        first_tunk = tmp_f
        second_tunk = tmp_s
        third_tunk = tmp_t
    Next i
    
    calc_swi_timelapse = swi_time_siries
End Function

Function unpack_guidance_grib2(filename) As GuidanceGrib2
    Dim base_info As BaseInfo

    buf = FreeFile
    
    Open filename For Binary As buf
    
    position = 0
    total_size = 0
    
    '第０～３節
    base_info = unpack_info(position, total_size, buf)
  
    
    Dim data() As GuidanceTimeSeries
    ReDim data(1)
    
    loop_count = 1
    prev_ft = 0
    
    Do
        n = UBound(data)
    
        '第４節
        section_size = get_dat(buf, position + 1, 4)
        span = get_dat(buf, position + 50, 4)
        ft = get_dat(buf, position + 19, 4) + span
        
        If prev_ft > ft Then
            loop_count = loop_count + 1
        End If
        
        position = position + section_size
        
        If span = 3 And loop_count = 2 Then
            
            '第５～７節
            value = unpack_data(position, buf, base_info.grid_num)
            
            data(n).ft = ft
            data(n).value = value
            
            If total_size - position <= 4 Then Exit Do
            ReDim Preserve data(n + 1)
        Else
            '第５～７節をスキップ
            section_size = get_dat(buf, position + 1, 4)
            position = position + section_size
            section_size = get_dat(buf, position + 1, 4)
            position = position + section_size
            section_size = get_dat(buf, position + 1, 4)
            position = position + section_size
        End If
        If total_size - position <= 4 Then Exit Do
        prev_ft = ft
    Loop

    ReDim Preserve data(UBound(data) - 1)
    unpack_guidance_grib2.base_info = base_info
    unpack_guidance_grib2.data = data
    
    Close buf
    Kill filename

End Function

Function unpack_swi_grib2(filename) As SwiGrib2
    Dim base_info As BaseInfo

    buf = FreeFile
    
    Open filename For Binary As #buf

    position = 0
    total_size = 0
    
    '第０～３節
    base_info = unpack_info(position, total_size, buf)
    
    Do While total_size - position > 4 'ファイルサイズの残りが4（第八節の長さ）以下になるまでループ
        '第４節
        section_size = get_dat(buf, position + 1, 4)
        data_type = get_dat(buf, position + 23, 1)
        data_sub_type = get_dat(buf, position + 25, 4)
        position = position + section_size
        '第５～７節
        If data_type = 200 Then '土壌雨量指数
            swi = unpack_data(position, buf, base_info.grid_num)
        ElseIf data_type = 201 And data_sub_type = 1 Then
            first_tunk = unpack_data(position, buf, base_info.grid_num)
        ElseIf data_type = 201 And data_sub_type = 2 Then
            second_tunk = unpack_data(position, buf, base_info.grid_num)
        Else
            MsgBox "土壌雨量指数、第1タンク値、第2タンク値以外のデータが見つかりました。処理を中断します。"
            Stop
        End If
    Loop
    
    unpack_swi_grib2.base_info = base_info
    unpack_swi_grib2.swi = swi
    unpack_swi_grib2.first_tunk = first_tunk
    unpack_swi_grib2.second_tunk = second_tunk
    
    Close buf
    Kill filename
End Function

Function get_dat(buf, s, length)

  '位置s～位置eの間のデータを取得して返す
  '複数データとなる場合は256のべき乗をかける（Big-Endian）
  Dim i
  Dim dat As Byte
  
  get_dat = 0
  dat = 0
  e = s + length - 1

  For i = s To e  's～eの数だけ繰り返し
     
    Get #buf, i, dat
    get_dat = get_dat + dat * (256 ^ (e - i))
    
  Next

End Function

Function unpack_info(ByRef position, ByRef total_size, buf) As BaseInfo
    '第０節
    total_size = get_dat(buf, 9, 8)
    position = 16
    
    '第１節
    section_size = get_dat(buf, position + 1, 4)
    initial_date = DateSerial(get_dat(buf, position + 13, 2), get_dat(buf, position + 15, 1), get_dat(buf, position + 16, 1))
    initial_time = TimeSerial(get_dat(buf, position + 17, 1), get_dat(buf, position + 18, 1), get_dat(buf, position + 19, 1))
    unpack_info.initial_date = initial_date + initial_time
    
    position = position + section_size
    
    '第３節
    section_size = get_dat(buf, position + 1, 4)
    unpack_info.grid_num = get_dat(buf, position + 7, 4) '全格子数
    unpack_info.x_num = get_dat(buf, position + 31, 4) '経線に沿った格子点数
    unpack_info.y_num = get_dat(buf, position + 35, 4) '緯線に沿った格子点数
    unpack_info.s_lat = get_dat(buf, position + 47, 4) '最初の格子点の緯度
    unpack_info.s_lon = get_dat(buf, position + 51, 4) '最初の格子点の経度
    unpack_info.e_lat = get_dat(buf, position + 56, 4) '最後の格子点の緯度
    unpack_info.e_lon = get_dat(buf, position + 60, 4) '最後の格子点の経度
    unpack_info.d_lon = get_dat(buf, position + 64, 4) 'i方向の増分
    unpack_info.d_lat = get_dat(buf, position + 68, 4) 'j方向の増分
    position = position + section_size
End Function

Function unpack_data(ByRef position, buf, grid_num)
    '第５節
    section_size = get_dat(buf, position + 1, 4)
    bit_num = get_dat(buf, position + 12, 1)   '１データのビット数
    level_max = get_dat(buf, position + 13, 2) '今回の圧縮に用いたレベルの最大値
    level_num = get_dat(buf, position + 15, 2) 'レベル最大値
    ReDim level(level_num)                     'レベル値
    fct = get_dat(buf, position + 17, 1)       '尺度因子
    For i = 1 To level_max
        level(i) = get_dat(buf, position + 16 + 2 * i, 2)
        If level(i) >= 65536 / 2 Then
            level(i) = level(i) - 65536 / 2
        End If
    Next
    position = position + section_size
                    
    '第６節
    section_size = get_dat(buf, position + 1, 4)
    position = position + section_size
    
    '第７節
    section_size = get_dat(buf, position + 1, 4)
    unpack_data = unpack_runlength(bit_num, level_num, level_max, grid_num, level, buf, position + 6, position + section_size)
    
    position = position + section_size
End Function

Function unpack_runlength(bit_num, level_num, level_max, grid_num, level, buf, s_position, e_position)
    lngu = 2 ^ bit_num - 1 - level_max 'ランレングス圧縮に用いる進数
    ReDim data(grid_num)
    d_index = 1
    p = s_position 'ランレングス解凍中のデータ位置
    
    Dim nlength As Long
    
    Do While p < e_position
        d = get_dat(buf, p, bit_num / 8)
        p = p + bit_num / 8
        If d > level_num Then
            MsgBox "第七節のランレングス解凍に失敗しました。処理を中断します"
            Stop
        End If
        dd = get_dat(buf, p, bit_num / 8)
        If dd <= level_max Then
            data(d_index) = level(d)
            d_index = d_index + 1
        Else
            nlength = 0 'ランレングス
            p2 = 1 'ランレングス検索用カウンタ
            Do While p <= e_position And dd > level_max
                nlength = nlength + ((lngu ^ (p2 - 1)) * (dd - level_max - 1))
                p = p + bit_num / 8
                dd = get_dat(buf, p, bit_num / 8)
                p2 = p2 + 1
            Loop
            For i = 1 To nlength + 1
                data(d_index) = level(d)
                d_index = d_index + 1
            Next
        End If
       
    Loop
    unpack_runlength = data

End Function


Sub calc_tunk_model(s1, s2, s3, t, r, ByRef s1_new, ByRef s2_new, ByRef s3_new)
   
    
    '流出孔の高さ(mm)
    l1 = 15
    l2 = 60
    l3 = 15
    l4 = 15

    '流出係数(1/hr)
    a1 = 0.1
    a2 = 0.15
    a3 = 0.05
    a4 = 0.01
    
    '浸透係数(1/hr)
    b1 = 0.12
    b2 = 0.05
    b3 = 0.01
    
    '流出量(mm/hr)
    q1 = 0
    q2 = 0
    q3 = 0
    
    If s1 > l1 Then
        q1 = q1 + a1 * (s1 - l1)
    End If
    If s1 > l2 Then
        q1 = q1 + a2 * (s1 - l2)
    End If
    
    If s2 > l3 Then
        q2 = a3 * (s2 - l3)
    End If
    
    If s3 > l4 Then
        q3 = a4 * (s3 - l4)
    End If
            
    '貯留高(mm)
    s1_new = (1 - b1 * t) * s1 - q1 * t + r
    s2_new = (1 - b2 * t) * s2 - q2 * t + b1 * s1 * t
    s3_new = (1 - b3 * t) * s3 - q3 * t + b2 * s2 * t
End Sub

Function meshcode_to_index(code As String)
    y = Val(Mid(code, 1, 2)) * 80 + Val(Mid(code, 5, 1)) * 10 + Val(Mid(code, 7, 1))
    x = Val(Mid(code, 3, 2)) * 80 + Val(Mid(code, 6, 1)) * 10 + Val(Mid(code, 8, 1))
    meshcode_to_index = Array(x, y)
End Function

Function meshcode_to_coordinate(code As String)
    '地域メッシュコードに対応する格子の中央の緯度経度を取得
    index = meshcode_to_index(code)
    x = index(0)
    y = index(1)
    lat = (y + 0.5) * 30 / 3600
    lon = (x + 0.5) * 45 / 3600 + 100
    meshcode_to_coordinate = Array(lat, lon)
End Function


Function get_data_num(lat, lon, base_info As BaseInfo)
    y = Int((base_info.s_lat / 1000000 - lat) / (base_info.d_lat / 1000000)) + 1
    x = Int((lon - base_info.s_lon / 1000000) / (base_info.d_lon / 1000000)) + 1
    get_data_num = (y - 1) * base_info.x_num + x
End Function
