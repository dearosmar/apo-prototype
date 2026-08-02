import SwiftUI

struct ReportView: View {
    let report: DocCheckResponse

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                overallCard
                extractedCard
                Text("항목별 신호등")
                    .font(.headline)
                    .foregroundStyle(AppColor.navy)
                ForEach(report.checks) { check in
                    checkCard(check)
                }
                Text("자동 점검은 참고용이에요. 큰 금액을 송금하기 전에는 반드시 은행·관세사와 함께 확인하세요.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .padding(.top, 4)
            }
            .padding()
        }
        .navigationTitle("점검 리포트")
        .navigationBarTitleDisplayMode(.inline)
        .background(Color(.systemGroupedBackground))
    }

    private var overallCard: some View {
        HStack(spacing: 14) {
            Text(AppColor.statusIcon(report.overall))
                .font(.system(size: 40))
            VStack(alignment: .leading, spacing: 6) {
                Text("종합 판정: \(AppColor.statusLabel(report.overall))")
                    .font(.title3.bold())
                    .foregroundStyle(AppColor.navy)
                Text(report.summary)
                    .font(.subheadline)
                if let label = report.label {
                    Text(label)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemBackground))
                .shadow(color: AppColor.navy.opacity(0.08), radius: 6, y: 2)
        )
        .overlay(alignment: .leading) {
            Rectangle()
                .fill(AppColor.status(report.overall))
                .frame(width: 5)
                .clipShape(RoundedRectangle(cornerRadius: 3))
        }
    }

    private var extractedCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("추출된 핵심 조건")
                .font(.headline)
                .foregroundStyle(AppColor.navy)
            row("결제조건", report.extracted.paymentTerms)
            row("선금 비율", report.extracted.depositPct.map { "\($0)%" })
            row("인코텀즈", report.extracted.incoterms)
            row("납기", report.extracted.leadTimeDays.map { "\($0)일" })
            row("수량", report.extracted.quantity.map { "\($0)개" })
            row("총액", report.extracted.totalAmount.map { String(format: "%.2f", $0) })
            row("수취인", report.extracted.beneficiary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemBackground))
                .shadow(color: AppColor.navy.opacity(0.08), radius: 6, y: 2)
        )
    }

    private func row(_ label: String, _ value: String?) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .frame(width: 84, alignment: .leading)
            Text(value ?? "미기재")
                .font(.subheadline)
                .foregroundStyle(value == nil ? AppColor.red : .primary)
            Spacer()
        }
    }

    private func checkCard(_ check: Check) -> some View {
        HStack(alignment: .top, spacing: 12) {
            Text(AppColor.statusIcon(check.status))
                .font(.title3)
            VStack(alignment: .leading, spacing: 4) {
                Text(check.item)
                    .font(.subheadline.bold())
                    .foregroundStyle(AppColor.status(check.status))
                Text(check.finding)
                    .font(.subheadline)
                Text("근거: \(check.basis)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(Color(.systemBackground))
                .shadow(color: AppColor.navy.opacity(0.06), radius: 4, y: 1)
        )
    }
}
