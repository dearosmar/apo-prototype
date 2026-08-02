import SwiftUI

struct ContentView: View {
    @State private var report: DocCheckResponse?
    @State private var loading = false
    @State private var errorMessage: String?
    @State private var navigate = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Spacer()
                Text("⚓")
                    .font(.system(size: 64))
                Text("바다 건너 사장님")
                    .font(.largeTitle.bold())
                    .foregroundStyle(AppColor.navy)
                Text("계약서(PI)를 촬영하면\n신호등 리포트로 위험을 알려드려요")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                Spacer()

                if let errorMessage {
                    Text(errorMessage)
                        .font(.footnote)
                        .foregroundStyle(AppColor.red)
                        .multilineTextAlignment(.center)
                }

                // TODO: #39 문서 스캔 버튼으로 교체
                Button {
                    Task { await runSample() }
                } label: {
                    if loading {
                        ProgressView().frame(maxWidth: .infinity)
                    } else {
                        Text("샘플 텍스트로 점검해 보기")
                            .font(.headline)
                            .frame(maxWidth: .infinity)
                    }
                }
                .padding()
                .background(AppColor.yellow)
                .foregroundStyle(AppColor.navy)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .disabled(loading)
            }
            .padding(24)
            .navigationDestination(isPresented: $navigate) {
                if let report {
                    ReportView(report: report)
                }
            }
        }
    }

    private func runSample() async {
        loading = true
        errorMessage = nil
        do {
            report = try await APIClient.shared.checkDocument(text: SampleData.riskyPI, filename: "sample.txt")
            navigate = true
        } catch {
            errorMessage = error.localizedDescription
        }
        loading = false
    }
}

enum SampleData {
    static let riskyPI = """
    PROFORMA INVOICE 形式发票
    Seller 卖方: 深圳市恒发贸易有限公司
    Description 品名: 毛绒玩具 (Plush Toys)
    Quantity 数量: 500 PCS
    Unit Price 单价: CNY 11.00 / PC
    Total Amount 总金额: CNY 5,500.00
    Trade Terms 贸易条款: EXW Shenzhen
    Payment Terms 付款方式: 100% T/T in advance 全款预付
    Beneficiary Bank 收款银行: Agricultural Bank of China
    Account Name 账户名: 王小明 (personal 个人账户)
    """
}

#Preview {
    ContentView()
}
