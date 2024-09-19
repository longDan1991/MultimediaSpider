// https://edith.xiaohongshu.com/api/sns/web/v1/feed

const req = {
  source_note_id: "66696f98000000000d00f289",
  image_formats: ["jpg", "webp", "avif"],
  extra: {
    need_body_topic: "1",
  },
  xsec_source: "pc_search",
  xsec_token: "AB2ngtDge1SBYqsH8NXPJ25gSUhp6t8636t7_R6HlT7dI=",
};

const res = {
  code: 0,
  success: true,
  msg: "成功",
  data: {
    cursor_score: "",
    items: [
      {
        id: "66696f98000000000d00f289",
        model_type: "note",
        note_card: {
          time: 1718185880000,
          last_update_time: 1718185881000,
          interact_info: {
            liked: false,
            liked_count: "44",
            collected: false,
            collected_count: "18",
            comment_count: "160",
            share_count: "12",
            followed: false,
            relation: "none",
          },
          image_list: [
            {
              file_id: "",
              height: 2048,
              width: 2048,
              trace_id: "",
              info_list: [
                {
                  image_scene: "WB_PRV",
                  url: "http://sns-webpic-qc.xhscdn.com/202409181841/bff0298c25a42f55870b1203b456f370/1040g008313ul3ln81c6g5o8vavbg961a6bl9og0!nd_prv_wlteh_webp_3",
                },
                {
                  url: "http://sns-webpic-qc.xhscdn.com/202409181841/a73813229398edf85761900823585f74/1040g008313ul3ln81c6g5o8vavbg961a6bl9og0!nd_dft_wlteh_webp_3",
                  image_scene: "WB_DFT",
                },
              ],
              url_pre:
                "http://sns-webpic-qc.xhscdn.com/202409181841/bff0298c25a42f55870b1203b456f370/1040g008313ul3ln81c6g5o8vavbg961a6bl9og0!nd_prv_wlteh_webp_3",
              url_default:
                "http://sns-webpic-qc.xhscdn.com/202409181841/a73813229398edf85761900823585f74/1040g008313ul3ln81c6g5o8vavbg961a6bl9og0!nd_dft_wlteh_webp_3",
              url: "",
              stream: {},
              live_photo: false,
            },
          ],
          tag_list: [
            {
              id: "5fa6043e0000000001008bbc",
              name: "客户资源",
              type: "topic",
            },
            {
              type: "topic",
              id: "5beaed6ef852e300011dce19",
              name: "精准客源",
            },
            {
              id: "5d32f1d9000000000f010c56",
              name: "电话销售",
              type: "topic",
            },
            {
              id: "5be8e73d47d0df0001b7cc87",
              name: "销售",
              type: "topic",
            },
          ],
          note_id: "66696f98000000000d00f289",
          type: "normal",
          title: "",
          desc: "#客户资源[话题]# #精准客源[话题]# #电话销售[话题]# 保证数\n据的准确性和及时性。所有区域和各行各业 企业名录及其联系方式。准确到可以直接和企业老板洽谈合作，并不是座机、前台号码等一些废号。\n让你不再盲目地去寻找客户，而是有针对性地帮你聚焦市场#销售[话题]#",
          user: {
            nickname: "d",
            avatar:
              "https://sns-avatar-qc.xhscdn.com/avatar/1040g2jo313ul4rlnhc6g5o8vavbg961ad3pp4g8",
            user_id: "611f57d7000000000100982a",
          },
          at_user_list: [],
          share_info: {
            un_share: false,
          },
        },
      },
    ],
    current_time: 1726656071911,
  },
};
