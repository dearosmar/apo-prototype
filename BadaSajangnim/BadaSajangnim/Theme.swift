import SwiftUI

enum AppColor {
    static let navy = Color(red: 11 / 255, green: 42 / 255, blue: 70 / 255)
    static let yellow = Color(red: 255 / 255, green: 188 / 255, blue: 0 / 255)
    static let green = Color(red: 27 / 255, green: 158 / 255, blue: 75 / 255)
    static let warning = Color(red: 232 / 255, green: 164 / 255, blue: 0 / 255)
    static let red = Color(red: 214 / 255, green: 69 / 255, blue: 69 / 255)

    static func status(_ value: String) -> Color {
        switch value {
        case "green": return green
        case "yellow": return warning
        default: return red
        }
    }

    static func statusIcon(_ value: String) -> String {
        switch value {
        case "green": return "🟢"
        case "yellow": return "🟡"
        default: return "🔴"
        }
    }

    static func statusLabel(_ value: String) -> String {
        switch value {
        case "green": return "안전"
        case "yellow": return "주의"
        default: return "위험"
        }
    }
}
