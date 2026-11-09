#include <windows.h>
#include <iostream>
#include <chrono>
#include <thread>

// Kiểm tra đồng thời Chuột Phải (RMB) và Chuột Trái (LMB)
bool IsAdsAndFiring() {
    bool lmb = (GetAsyncKeyState(VK_LBUTTON) & 0x8000) != 0;
    bool rmb = (GetAsyncKeyState(VK_RBUTTON) & 0x8000) != 0;
    return lmb && rmb;
}

// Di chuyển chuột tương đối theo chiều dọc (Y)
void MoveMouseRelative(int dy) {
    if (dy != 0) {
        mouse_event(MOUSEEVENTF_MOVE, 0, (DWORD)dy, 0, 0);
    }
}

int main() {
    // Ẩn cửa sổ dòng lệnh đen (Console) nếu muốn chạy ngầm ẩn danh
    // HWND hwnd = GetConsoleWindow();
    // ShowWindow(hwnd, SW_HIDE);

    std::cout << "=== RECOIL CONTROL C++ ===" << std::endl;
    std::cout << "Giu Chuot Phai (ADS) + Chuot Trai (Ban) de ghim tam." << std::endl;
    std::cout << "Nhan phim ESC de thoat chuong trinh." << std::endl;

    double pull_speed_pps = 15.0; // Tốc độ kéo dọc (Pixels / giây)
    double accum_y = 0.0;

    auto last_time = std::chrono::high_resolution_clock::now();

    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = now - last_time;
        last_time = now;
        double dt = elapsed.count();

        if (IsAdsAndFiring()) {
            // Tích lũy sub-pixel theo thời gian thực
            accum_y += pull_speed_pps * dt;
            int move_y = static_cast<int>(accum_y);
            
            if (move_y != 0) {
                MoveMouseRelative(move_y);
                accum_y -= move_y;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        } else {
            accum_y = 0.0;
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }

        // Nhấn ESC để thoát nhanh
        if (GetAsyncKeyState(VK_ESCAPE) & 0x8000) {
            break;
        }
    }

    return 0;
}
