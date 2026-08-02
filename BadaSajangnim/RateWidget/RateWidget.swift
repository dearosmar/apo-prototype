import SwiftUI
import WidgetKit

// 데모 스냅숏 — backend/data/snapshots/exchange_rates_sample.json(수출입은행 AP01)과 동일 값.
// TODO: 환율 엔드포인트가 생기면 App Group 캐시로 교체 (위젯 직접 통신은 로컬 네트워크 권한 제약)
enum RateSnapshot {
    static let currencyName = "위안화 CNH"
    static let rate = 191.67
    static let previousRate = 190.84
    static let basis = "2026-07-25 스냅숏 기준"
    static var paymentDue: Date {
        Calendar.current.date(from: DateComponents(year: 2026, month: 8, day: 29)) ?? .now
    }
}

struct RateEntry: TimelineEntry {
    let date: Date

    var diff: Double { RateSnapshot.rate - RateSnapshot.previousRate }
    var diffPercent: Double { diff / RateSnapshot.previousRate * 100 }
    var dDay: Int {
        Calendar.current.dateComponents(
            [.day],
            from: Calendar.current.startOfDay(for: date),
            to: Calendar.current.startOfDay(for: RateSnapshot.paymentDue)
        ).day ?? 0
    }
}

struct RateProvider: TimelineProvider {
    func placeholder(in context: Context) -> RateEntry {
        RateEntry(date: .now)
    }

    func getSnapshot(in context: Context, completion: @escaping (RateEntry) -> Void) {
        completion(RateEntry(date: .now))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<RateEntry>) -> Void) {
        let now = Date()
        let nextHour = Calendar.current.date(byAdding: .hour, value: 1, to: now) ?? now
        completion(Timeline(entries: [RateEntry(date: now)], policy: .after(nextHour)))
    }
}

private let navy = Color(red: 11 / 255, green: 42 / 255, blue: 70 / 255)
private let yellow = Color(red: 255 / 255, green: 188 / 255, blue: 0 / 255)

struct RateWidgetView: View {
    @Environment(\.widgetFamily) private var family
    let entry: RateEntry

    var body: some View {
        content
            .containerBackground(for: .widget) { navy }
    }

    @ViewBuilder
    private var content: some View {
        switch family {
        case .systemMedium: medium
        default: small
        }
    }

    private var rateBlock: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(RateSnapshot.currencyName)
                .font(.caption2)
                .foregroundStyle(.white.opacity(0.75))
            Text(String(format: "%.2f원", RateSnapshot.rate))
                .font(.system(size: 24, weight: .bold, design: .rounded))
                .foregroundStyle(.white)
                .minimumScaleFactor(0.7)
            HStack(spacing: 3) {
                Image(systemName: entry.diff >= 0 ? "arrowtriangle.up.fill" : "arrowtriangle.down.fill")
                    .font(.system(size: 9))
                Text(String(format: "%+.2f (%+.2f%%)", entry.diff, entry.diffPercent))
                    .font(.caption2.bold())
            }
            .foregroundStyle(entry.diff >= 0 ? Color(red: 1, green: 0.45, blue: 0.42) : Color(red: 0.4, green: 0.85, blue: 0.6))
        }
    }

    private var basisBlock: some View {
        Text(RateSnapshot.basis)
            .font(.system(size: 8))
            .foregroundStyle(.white.opacity(0.5))
    }

    private var small: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("⚓ 바다 건너 사장님")
                .font(.system(size: 9, weight: .semibold))
                .foregroundStyle(yellow)
            Spacer(minLength: 0)
            rateBlock
            Spacer(minLength: 0)
            basisBlock
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var medium: some View {
        HStack(spacing: 14) {
            VStack(alignment: .leading, spacing: 6) {
                Text("⚓ 바다 건너 사장님")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundStyle(yellow)
                Spacer(minLength: 0)
                rateBlock
                Spacer(minLength: 0)
                basisBlock
            }
            Spacer()
            VStack(spacing: 4) {
                Text("결제일까지")
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.75))
                Text(entry.dDay >= 0 ? "D-\(entry.dDay)" : "D+\(-entry.dDay)")
                    .font(.system(size: 26, weight: .heavy, design: .rounded))
                    .foregroundStyle(yellow)
                Text("8/29 잔금 송금")
                    .font(.system(size: 9))
                    .foregroundStyle(.white.opacity(0.6))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(RoundedRectangle(cornerRadius: 12).fill(.white.opacity(0.08)))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct RateWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "RateWidget", provider: RateProvider()) { entry in
            RateWidgetView(entry: entry)
        }
        .configurationDisplayName("환율·결제 D-day")
        .description("결제 통화 환율과 잔금 송금일까지 남은 날을 보여줘요.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}

#Preview(as: .systemMedium) {
    RateWidget()
} timeline: {
    RateEntry(date: .now)
}
