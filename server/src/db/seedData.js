// Mock Database for Government-to-Citizen (G2C) Interoperability Platform

export const db = {
  // G2C Registered Citizen Profiles (Simulated DigiLocker / e-KYC Registry)
  users: [
    {
      id: "CIT-001",
      name: "Ramesh Dattatray Patil",
      type: "CITIZEN",
      pan: "RMPTL1234F",
      aadhaar: "998877665544",
      authorizedPerson: "Ramesh Dattatray Patil",
      phone: "+91 98765 43210",
      maskedPhone: "98765*****0",
      email: "ramesh.patil@gmail.com",
      address: "House 42, Gram Panchayat Kothrud, Haveli, Pune, Maharashtra - 411038",
      kycVerified: true,
      digilockerId: "DL-MH-CIT-90123",
      registeredLandSurvey: "101"
    },
    {
      id: "CIT-002",
      name: "Sunita Ashok Deshmukh",
      type: "CITIZEN",
      pan: "SNDSH5678K",
      aadhaar: "887766554433",
      authorizedPerson: "Sunita Ashok Deshmukh",
      phone: "+91 98123 45678",
      maskedPhone: "98123*****8",
      email: "sunita.deshmukh@yahoo.in",
      address: "Plot 14, Village Pirangut, Mulshi, Pune, Maharashtra - 412115",
      kycVerified: true,
      digilockerId: "DL-MH-CIT-54312",
      registeredLandSurvey: "102"
    },
    {
      id: "CIT-003",
      name: "Priya Ramesh Sharma",
      type: "CITIZEN",
      pan: "PRSHM9012L",
      aadhaar: "123456789012",
      authorizedPerson: "Priya Ramesh Sharma",
      phone: "+91 99001 12233",
      maskedPhone: "99001*****3",
      email: "priya.sharma@gmail.com",
      address: "Flat 402, Green Acres, Kothrud, Pune, Maharashtra - 411038",
      kycVerified: true,
      digilockerId: "DL-MH-CIT-11209",
      registeredLandSurvey: "103"
    },
    {
      id: "CIT-004",
      name: "Ganesh Vishnu Kulkarni",
      type: "CITIZEN",
      pan: "GNKLK3456P",
      aadhaar: "556677889900",
      authorizedPerson: "Ganesh Vishnu Kulkarni",
      phone: "+91 97654 32109",
      maskedPhone: "97654*****9",
      email: "ganesh.kulkarni@hotmail.com",
      address: "Wada 12, Village Chakan, Khed, Pune, Maharashtra - 410501",
      kycVerified: true,
      digilockerId: "DL-MH-CIT-78901",
      registeredLandSurvey: "104"
    },
    {
      id: "CIT-005",
      name: "Ananya Suresh Joshi",
      type: "CITIZEN",
      pan: "ANJSH7890M",
      aadhaar: "443322110099",
      authorizedPerson: "Ananya Suresh Joshi",
      phone: "+91 96543 21098",
      maskedPhone: "96543*****8",
      email: "ananya.joshi@outlook.com",
      address: "Survey 105, Baramati Tehsil, Pune, Maharashtra - 413102",
      kycVerified: true,
      digilockerId: "DL-MH-CIT-45678",
      registeredLandSurvey: "105"
    }
  ],

  // Land Department Data Store (Legacy Regional Format for Citizens)
  landRecords: {
    "101": {
      gtn: "101",
      malak_name: "ABC Industries Pvt Ltd",
      malak_pan: "ABCDE1234F",
      malak_aadhaar: "998877665544",
      kshetra: "8.0",
      kshetra_unit: "HA",
      jamabandi: "APPROVED",
      jamin_prakar: "INDUSTRIAL",
      bandhak: false,
      court_case: false,
      jilha: "Pune",
      taluka: "Haveli",
      gaw: "Wagholi",
      last_updated: "2026-08-10T10:00:00Z"
    },
    "102": {
      gtn: "102",
      malak_name: "Sunita Ashok Deshmukh",
      malak_pan: "SNDSH5678K",
      malak_aadhaar: "887766554433",
      kshetra: "1.8",
      kshetra_unit: "HA",
      jamabandi: "PENDING", // Mutation Pending (Inheritance Transfer)
      jamin_prakar: "AGRICULTURAL",
      bandhak: false,
      court_case: false,
      jilha: "Pune",
      taluka: "Mulshi",
      gaw: "Pirangut",
      last_updated: "2026-09-01T14:30:00Z"
    },
    "103": {
      gtn: "103",
      malak_name: "Priya Ramesh Sharma",
      malak_pan: "PRSHM9012L",
      malak_aadhaar: "123456789012",
      kshetra: "0.75",
      kshetra_unit: "HA",
      jamabandi: "APPROVED",
      jamin_prakar: "RESIDENTIAL",
      bandhak: true, // Mortgage encumbrance active
      court_case: false,
      jilha: "Pune",
      taluka: "Haveli",
      gaw: "Kothrud",
      last_updated: "2026-07-18T09:15:00Z"
    },
    "104": {
      gtn: "104",
      malak_name: "Ganesh Vishnu Kulkarni",
      malak_pan: "GNKLK3456P",
      malak_aadhaar: "556677889900",
      kshetra: "4.2",
      kshetra_unit: "HA",
      jamabandi: "UNDER_OBJECTION",
      jamin_prakar: "AGRICULTURAL",
      bandhak: false,
      court_case: true, // Boundary dispute court case
      jilha: "Pune",
      taluka: "Khed",
      gaw: "Chakan",
      last_updated: "2026-08-25T11:45:00Z"
    },
    "105": {
      gtn: "105",
      malak_name: "Ananya Suresh Joshi",
      malak_pan: "ANJSH7890M",
      malak_aadhaar: "443322110099",
      kshetra: "3.1",
      kshetra_unit: "HA",
      jamabandi: "APPROVED",
      jamin_prakar: "AGRICULTURAL",
      bandhak: false,
      court_case: false,
      jilha: "Pune",
      taluka: "Baramati",
      gaw: "Baramati",
      last_updated: "2026-08-30T16:20:00Z"
    }
  },

  // In-Memory Active OTP sessions
  activeOtps: new Map(),

  // Simulated Audit Logs
  auditLogs: []
};
