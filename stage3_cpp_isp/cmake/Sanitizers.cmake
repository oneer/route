function(cpp_isp_enable_sanitizers target_name)
    # Sanitizer 默认关闭，避免影响普通性能 benchmark；需要查内存错误时用 CMake 选项开启。
    if(NOT CPP_ISP_ENABLE_ASAN)
        return()
    endif()

    if(MSVC)
        target_compile_options(${target_name} PRIVATE /fsanitize=address)
    else()
        # fno-omit-frame-pointer 让 ASAN 报告里的调用栈更完整。
        target_compile_options(${target_name} PRIVATE -fsanitize=address -fno-omit-frame-pointer)
        target_link_options(${target_name} PRIVATE -fsanitize=address)
    endif()
endfunction()
