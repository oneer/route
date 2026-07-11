function(cpp_isp_apply_compiler_options target_name)
    # 统一打开较严格警告：教学项目更希望早暴露窄化、未使用变量等小问题。
    if(MSVC)
        # 源码和注释统一为 UTF-8；否则中文 Windows 的 ACP 936 会误解 UTF-8 字节，
        # 不仅产生 C4819，还可能让后续 C++ token 被错误解析。
        target_compile_options(${target_name} PRIVATE /W4 /permissive- /utf-8)
    else()
        target_compile_options(${target_name} PRIVATE -Wall -Wextra -Wpedantic)
        if(MINGW)
            # MinGW 下静态链接运行时，减少把可执行文件拷到其它机器时缺 DLL 的概率。
            target_link_options(${target_name} PRIVATE -static-libgcc -static-libstdc++)
        endif()
    endif()
endfunction()
