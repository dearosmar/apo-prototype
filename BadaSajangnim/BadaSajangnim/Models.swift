import Foundation

struct DocCheckResponse: Codable {
    let filename: String
    let label: String?
    let extracted: Extracted
    let checks: [Check]
    let overall: String
    let summary: String
    let fallback: Bool
}

struct Extracted: Codable {
    let paymentTerms: String?
    let depositPct: Int?
    let incoterms: String?
    let leadTimeDays: Int?
    let quantity: Int?
    let unitPrice: Double?
    let totalAmount: Double?
    let beneficiary: String?
    let personalAccount: Bool?

    enum CodingKeys: String, CodingKey {
        case paymentTerms = "payment_terms"
        case depositPct = "deposit_pct"
        case incoterms
        case leadTimeDays = "lead_time_days"
        case quantity
        case unitPrice = "unit_price"
        case totalAmount = "total_amount"
        case beneficiary
        case personalAccount = "personal_account"
    }
}

struct Check: Codable, Identifiable {
    let item: String
    let status: String
    let finding: String
    let basis: String

    var id: String { item }
}
