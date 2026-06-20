function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(document).ready(function() {
    const $likeBtn = $('#like-btn');
    
    if ($likeBtn.length) {
        $likeBtn.on('click', function() {
            const postId = $(this).attr('data-post-id');
            const $this = $(this);
            
            $.ajax({
                url: `/post/${postId}/like/`,
                type: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                },
                contentType: 'application/json',
                success: function(data) {
                    if (data.error) {
                        alert(data.error);
                    } else {
                        $this.text(data.liked ? '❤️ 取消' : '🤍 いいね');
                        $('#like-count').text(data.total_likes);
                    }
                },
                error: function(xhr, status, error) {
                    console.log("通信エラーが発生しました: " + error);
                }
            });
        });
    }
});
